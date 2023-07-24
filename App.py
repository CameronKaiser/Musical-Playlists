import numpy as np
import soundfile as sf
from pathlib import Path
from Note import Note
import tkinter.filedialog
import Analyzer
import multiprocessing
from multiprocessing import Pool
from math import ceil
import time
import Playlists

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

chromaticScale          = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
supportedFileExtensions = ["WAV", "AIFF", "AU", "RAW", "PAF", "SVX", "NIST", "VOC", "IRCAM", "W64", "MAT4", "MAT5", "PVF", "XI",
                           "HTK", "SDS", "AVR", "WAVEX", "SD2", "FLAC", "CAF", "WVE", "OGG", "MPC2K", "RF64", "MPEG", "MP3"]

stuttgartPitch        = 440    # A4
twelthRoot            = pow(2, (1 / 12.0))
overlapCoefficient    = 0.661  # optimal Blackman-Harris overlap
sequencingCoefficient = 1 / 4  # Analysis iteration increment, in proportion of a second
increments            = 10     # Amount of windows to be analyzed per buffer - must be even

segmentSize      = 32768       # FFT size
overlapOffset    = int((segmentSize / 2) + (segmentSize - (segmentSize * overlapCoefficient)))
segmentIncrement = int(segmentSize + (segmentSize * overlapCoefficient) / increments)
blackmanWindow   = np.blackman(segmentSize)

cores = multiprocessing.cpu_count()  # Number of cores to be used in multiprocessing
genre = "Orchestral"                 # Can be used to opt for different types of analyses

index = 0
noteDictionary = {}       # Build dictionary of notes
for i in range(-57, 52):  # C0 - C9

    pitchClass = chromaticScale[index % 12]
    octave     = index // 12
    frequency  = stuttgartPitch * pow(twelthRoot, i)

    noteDictionary[pitchClass + str(octave)] = Note(pitchClass, octave, frequency)

    index += 1

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():

    #   Prompt the user to select a folder, adding all valid tracks to list
        tracks = getPlaylist()

    #   Add configuration and genre to each track
        for track in tracks:
            track.configuration = Analyzer.Configuration("Orchestral")
            track.genre         = genre

    #   Determine how many tracks should be processed by each core
        chunkSize = int(ceil(len(tracks) / cores))

    #   Analyse tracks using multiprocessing
        pool = Pool(processes = cores)
        analyzedTracks = pool.map(analyzeTrack, tracks, chunkSize)
        pool.close()

    #   Create playlist of the given tracks
        playlist: list[Track] = Playlists.buildPlaylist(analyzedTracks)

        for track in playlist:
            print(track.easyKey + " ~ " + track.name)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Track:

    #   The Track object is initialized with the file path of a track and contains its metadata

        def __init__(self, filePath, extension, name):
            self.filePath      = filePath
            self.extension     = extension
            self.name          = name
            self.startKey      = None
            self.endKey        = None
            self.easyKey       = None
            self.length        = None
            self.configuration = None
            self.genre         = None
            self.halfwaySample = None
            self.presence      = dict.fromkeys(chromaticScale, 0.0)
            self.startPresence = dict.fromkeys(chromaticScale, 0.0)
            self.endPresence   = dict.fromkeys(chromaticScale, 0.0)


class Key:

    #   The Key object includes the tonics of a piece and whether the key is minor or major-based

        def __init__(self, tonic, mode):
            self.tonic = tonic
            self.mode  = mode


class Buffer:

    #   The Buffer object holds an analysis performed on a discrete time frame of
    #   a track, along with other related metrics

        def __init__(self, analysis, dcOffset, sampleRate, sample):
            self.analysis   = analysis
            self.dcOffset   = dcOffset
            self.binSize    = sampleRate / len(analysis)
            self.sampleRate = sampleRate
            self.sample     = sample

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def getPlaylist(directoryPath = None):

    #   Get and return a list of tracks from the user's device

    #   If no path is specified, prompt the user to select a folder
        if directoryPath == None:

            root = tkinter.Tk()
            root.withdraw()

            directoryPath = Path(tkinter.filedialog.askdirectory(mustexist = True))

            root.destroy()

        else:
            directoryPath = Path(directoryPath)

        filePaths = directoryPath.glob('*')

        tracks: list[Track] = []

    #   Create a list of Track objects. Non-compatible files will be ignored
        for filePath in filePaths:
            extension = filePath.suffix[1:]
            name = filePath.stem
            if extension.upper() in supportedFileExtensions:
                tracks.append(Track(str(filePath), extension, name))
            else:
                print(str(filePath) + " is not a supported audio file")

        return tracks


def analyzeTrack(track):

    #   Get audio data and sampling rate from track
        data, sampleRate = sf.read(track.filePath, always_2d=True)

    #   Convert to mono for fourier transform
        data = convertToMono(data)

        seconds             = len(data) / sampleRate
        track.length        = str(int(seconds // 60)) + ":" + str(int(seconds % 60)).zfill(2)
        track.halfwaySample = int(len(data) / 2)

        sequencingIncrement = int(sequencingCoefficient * sampleRate)  # Time value to iterate by

    #   Iterate through the track
        for i in range(0, int(seconds / sequencingCoefficient)):

            sample = i * sequencingIncrement

            timer = int(time.time() * 1000)
            analyses = getSegmentAnalyses(data, sample)
            #print("Analyzed in: "  + str(int(time.time() * 1000) - timer))

        #   Average all segments
            analysis = np.average(analyses, axis=0)

        #   Collect the DC offset (zero-frequency) and remove it to make the array length coincide with samples / 2
            dcOffset = analysis[0]
            analysis = analysis[1:]

            buffer = Buffer(analysis, dcOffset, sampleRate, sample)

        #   If the max power of our analysis is greater than 10, we can assume it is more than just signal noise
        #   and will add the power of any fundamentals to our notePresence dictionaries
            if max(buffer.analysis) > 10:
                appendNotePresence(buffer, track)

        assignTrackKeys(track)

        return track


def convertToMono(trackData):

    #   Converts a track to mono for FFT analysis

        monoData = np.empty(len(trackData), dtype=np.float64)
        for i in range(0, len(trackData)):
            frame = trackData[i]

        #   The always_2d parameter seems to be bugged, so we have to check ourselves
            if len(frame) > 1:
                monoData[i] = frame[0] + frame[1]
            else:
                monoData[i] = frame[0]

        return monoData


def getSegmentAnalyses(monoData, sample):

    #   Using a sample size of half a second, apply a blackman-harris window and zero-padded FFT operation on
    #   100 segments before and after current sample, with an overlap of 66.1%. The segments are then averaged
    #   into one analysis. The windowing and smoothing helps to refine results and reduce spectral leakage

        segmentStart = sample - overlapOffset

        #segments = np.empty(increments, dtype=object)
        analyses = []

        for i in range(0, increments):
            #   Since the smoothing operation grabs samples before and after a given point, we must omit segments that
            #   exceed the outer bounds of our data
            if segmentStart < 0 or segmentStart + segmentIncrement > len(monoData):
                segmentStart += segmentIncrement
                continue

            analyses.append(analyzeSegment(monoData[segmentStart : segmentStart + segmentSize]))
            segmentStart += segmentIncrement

        return analyses


def analyzeSegment(segment):

    #   Takes a set of segmentSize samples, applies a blackman harris window, and returns the realized FFT'd output

    #   Apply blackman-harris window function
        segment *= blackmanWindow

    #   Perform zero-padded FFT on the segment, convert the complex output to real, and get the absolute value
        spectrumData = np.fft.rfft(segment)
        spectrumData = np.absolute(np.real(spectrumData))

        return spectrumData


def appendNotePresence(buffer, track):

    #   Takes a buffer and a dictionary of chromatic notes, determining if any peaks
    #   in the buffer's analysis are fundamental tones, adding their powers to the
    #   respective note of the dictionary if they are

        average = sum(buffer.analysis) / len(buffer.analysis)

        for noteName in noteDictionary:
            note = noteDictionary[noteName]

            #   Power above the 6th octave is unlikely to be that of a fundamental's
            if note.octave >= 6:
                continue

            notePower = note.getPower(buffer)

        #   check adjacent notes to see if current note is a peak
            neighborPowers = []
            neighborPowers.append(note.getAdjacent( 1).getPower(buffer))
            neighborPowers.append(note.getAdjacent(-1).getPower(buffer))

        #   If the note's power is greater than that of its neighbors, a peak has been detected
            if notePower > max(neighborPowers):
                overtones = note.getOvertones()

                validOvertones = 0

            #   Iterate through all overtones of the note, increasing score for those that appear to be significant
                for overtone in overtones:
                    overtoneNeighborPowers = []
                    overtoneNeighborPowers.append(overtone.getAdjacent( 1).getPower(buffer))
                    overtoneNeighborPowers.append(overtone.getAdjacent(-1).getPower(buffer))

                    overtonePower = overtone.getPower(buffer)
                    if overtonePower > max(overtoneNeighborPowers) or (overtonePower > average and overtonePower > max(overtoneNeighborPowers) * 0.8):
                        validOvertones += 1

            #   If 10 or more overtones of the given note show considerable power, the note is likely a fundamental
            #   Add its power to the note presence dictionary, as well as the starting and ending dictionaries
                if validOvertones >= 10:
                    track.presence[note.pitchClass] += notePower
                    if buffer.sample < track.halfwaySample:
                        track.startPresence[note.pitchClass] += notePower
                    else:
                        track.endPresence[note.pitchClass]   += notePower


def assignTrackKeys(track):

    #   Identifies and assigns the key(s) of a track

        generalTonic = calculateTonic(track.presence, track.configuration)
        generalMode  = getMode(generalTonic, track.presence)

        startTonic = calculateTonic(track.startPresence, track.configuration)
        endTonic   = calculateTonic(track.endPresence  , track.configuration)

        if track.genre == "Pop" or startTonic == endTonic:
            track.startKey = Key(generalTonic, generalMode)
            track.endKey   = Key(generalTonic, generalMode)
            track.easyKey  = generalTonic

        else:
            track.startKey = Key(startTonic, getMode(startTonic, track.startPresence))
            track.endKey   = Key(endTonic  , getMode(endTonic  , track.endPresence))
            track.easyKey = startTonic + " - " + endTonic


def calculateTonic(presence, configuration):

    #   Takes an array of note presences and uses the given configuration to estimate the tonal center of the data
    #   Notes' final scores will be scaled relatively to their power level relative to the principal power (max power)

        noteScores = {}

        for note in presence:
            tonalityScorer = Analyzer.TonalityScorer(presence, note, configuration)

            score = 0

            score += tonalityScorer.significance()
            score += tonalityScorer.dominantRelationship()
            score += tonalityScorer.dominantSubdominantRelationship()
            score += tonalityScorer.minorRelativeRelationship()
            score += tonalityScorer.majorRelativeRelationship()
            score += tonalityScorer.triadicRelationship()
            score += tonalityScorer.leadingToneRelationship()
            score += tonalityScorer.tritoneRelationship()
            score += tonalityScorer.phrygianRelationship()
            score += tonalityScorer.diatonicRelationship()

            noteScores[note] = round(score * 10, 2)

    #   Order the notes by score to retrieve the highest scoring note
        noteScores = dict(sorted(noteScores.items(), key=lambda x: x[1], reverse=True))

        return list(noteScores.keys())[0]


def getMode(note, presence):

    #   Takes a key and array of note presences to determine whether said key is minor or major

        noteIndex = chromaticScale.index(note)
        minorModalPower = (presence[chromaticScale[(noteIndex + 3) % 12]]
                        +  presence[chromaticScale[(noteIndex + 8) % 12]])

        majorModalPower = (presence[chromaticScale[(noteIndex + 4) % 12]]
                        +  presence[chromaticScale[(noteIndex + 9) % 12]])

        return "minor" if minorModalPower > majorModalPower else "major"


def getTimestamps(buffer: Buffer):

    #   Returns the start and end time of a given buffer

        timeStart      = (buffer.sample - len(buffer.analysis)) / buffer.sampleRate  # in seconds
        minutesStart   = int(timeStart // 60)
        secondsStart   = int(timeStart % 60)
        hundrethsStart = int(((timeStart - int(timeStart)) * 100))

        timeEnd        = (buffer.sample + len(buffer.analysis)) / buffer.sampleRate  # in seconds
        minutesEnd     = int(timeEnd // 60)
        secondsEnd     = int(timeEnd % 60)
        hundrethsEnd   = int(((timeEnd - int(timeEnd)) * 100))

        return "{0}:{1}:{2}".format(str(minutesStart), str(secondsStart).zfill(2), str(hundrethsStart).zfill(2)) + " - " \
             + "{0}:{1}:{2}".format(str(minutesEnd),   str(secondsEnd).zfill(2),   str(hundrethsEnd).zfill(2))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()



