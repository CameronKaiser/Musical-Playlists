from Note import Note
from App import Track
from App import Key
import random
import collections

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

keys       = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
minorScale = [0, 2, 3, 5, 7, 8, 10]
majorScale = [0, 2, 4, 5, 7, 9, 11]

harmonicCoefficient   = 3
diatonicCoefficient   = 0.5
neighborCoefficient   = 2
historicalCoefficient = 1
randomCoefficient     = 2

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def buildPlaylist(tracks: list[Track]):

    #   Constructs a playlist using harmonic and musical convention

        playlist      = []
        keylist       = []
        playlistSize  = len(tracks)
        keyBuffer     = collections.deque(maxlen = playlistSize // 5 if playlistSize < 50 else 10)
        startingTrack = tracks[random.randint(0, len(tracks) - 1)]

        playlist .append(startingTrack)
        tracks   .remove(startingTrack)
        keylist  .append(startingTrack.startKey)
        keyBuffer.append(startingTrack.startKey)
        if startingTrack.startKey.tonic != startingTrack.endKey.tonic:
            keylist  .append(startingTrack.endKey)
            keyBuffer.append(startingTrack.endKey)

        for i in range(1, playlistSize):

            previousTrack = playlist[i - 1]
            previousKey   = previousTrack.endKey

            keyScores = dict.fromkeys(keys, 0.0)

            scoreHarmonicProximity(previousKey, keyScores)
            scoreDiatonicProximity(previousKey, keyScores)
            scoreNeighborProximity(keylist    , keyScores)
            scoreHistoricProximity(keyBuffer  , keyScores)

        #   Randomize results a bit to make app reusable
            for key in keyScores:
                keyScores[key] += random.uniform(randomCoefficient * -1, randomCoefficient)

        #   Order the notes by score to retrieve the highest scoring note
            keyScores = dict(sorted(keyScores.items(), key=lambda x: x[1], reverse=True))

        #   Shuffle remaining tracks and choose next track, prioritizing based on keyScores
            random.shuffle(tracks)
            nextTrack = None
            for key in keyScores:
                for track in tracks:
                    if track.startKey.tonic == key:
                        nextTrack = track
                        break

                if nextTrack is not None:
                    break

            playlist.append(nextTrack)
            tracks.remove(nextTrack)

            keylist  .append(nextTrack.startKey)
            keyBuffer.append(nextTrack.startKey)
            if nextTrack.startKey != nextTrack.endKey:
                keylist  .append(nextTrack.endKey)
                keyBuffer.append(nextTrack.endKey)

        return playlist


def scoreNeighborProximity(keylist, keyScores):

    #   Increases the score of a previous neighbor in the case of 2nd movement (e.g. C - D), but only if we are certain
    #   this is an isolated 2nd movement, so as to not create infinite neighbor loops. Results in higher chance of C - D - C

        def neighborKeys(keyA, keyB):

            #   Returns true if the two given keys are within a second in proximity of each other (2 halfsteps)

            if (abs(keys.index(keyA.tonic) - keys.index(keyB.tonic)) <= 2
            or  abs(keys.index(keyA.tonic) - keys.index(keyB.tonic)) >= len(keys) - 2):
                return True

            return False

        keylistSize = len(keylist)
        if keylistSize >= 2:

            currentKey  = keylist[keylistSize - 1]
            previousKey = keylist[keylistSize - 2]

        #   Check if last two keys are a second apart
            if neighborKeys(currentKey, previousKey):

            #   Check to make sure we aren't perpetuating a neighbortone loop
                if keylistSize > 2:

                    tertiaryKey = keylist[keylistSize - 3]

                    if not neighborKeys(previousKey, tertiaryKey):
                        keyScores[previousKey.tonic] += 1 * neighborCoefficient


def scoreHarmonicProximity(key, keyScores):

    #   Increases the score of keys in close harmonic proximity, e.g. A and G for key D

        tonic = Note(key.tonic, 4, 0)

        keyScores[tonic.pitchClass] += 1
        for i in range(1, 6):
            keyScores[tonic.getAdjacent(i *  7).pitchClass] += round(1 / i, 2) * harmonicCoefficient
            keyScores[tonic.getAdjacent(i * -7).pitchClass] += round(1 / i, 2) * harmonicCoefficient


def scoreDiatonicProximity(key, keyScores):

    #   Increases the score of keys that fall under the current key's diatonic collection

        tonic = Note(key.tonic, 4, 0)
        scale = minorScale if key.mode == "minor" else majorScale

        for i in scale:
            keyScores[tonic.getAdjacent(i).pitchClass] += 1 * diatonicCoefficient


def scoreHistoricProximity(keyBuffer, keyScores):

    #   Increases the score of keys that were present recently in the playlist

            for key in keyBuffer:
                keyScores[key.tonic] += (1 / len(keyBuffer)) * historicalCoefficient


def getCircleOfFifths(key, keyScores):

    tonic = Note(key.tonic, 4, 0)

    keyRanks   = []
    currentKey = Note(key.tonic, 4, 0)

    for i in range(0, 12):
        keyRanks.append(currentKey.pitchClass)
        currentKey = currentKey.getAdjacent(7)

    return keyRanks