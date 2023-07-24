import math

stuttgartPitch   = 440  # A4
twelthRoot       = pow(2, (1/12.0))
chromaticScale   = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
overtoneSequence = {12 :   0,     # Steps : Cents
                    19 :   2,     # Many overtones don't align exactly with equal temperament,
                    24 :   0,     # so we include the cents difference to ensure we can
                    28 : -14,     # determine the exact frequency of the overtone
                    31 :   2,
                    34 : -31,
                    36 :   0,
                    38 :   2,
                    40 : -14,
                    42 : -49,
                    43 :   2,
                    44 :  41,
                    46 : -31,
                    47 : -12,
                    48 :   0}

# -----------------------------------------------------------------------------------
#           ~ Note ~
#   The Note object is a tonal note (e.g. A4) with a specific frequency assigned to
#   it. The frequency is assigned via constructor so that intonation can be handled
#   precisely (e.g. A4 is 440hz, but A4 as the 2nd overtone of D3 is 440.494hz, as
#   notes are typically equal temperament tuning whereas overtones are exact ratios)
# -----------------------------------------------------------------------------------

class Note:
    def __init__(self, pitchClass, octave, frequency):
        self.name                    = pitchClass + str(octave)
        self.pitchClass              = pitchClass
        self.octave                  = octave
        self.frequency               = frequency
        self.semitonesAboveStuttgart = 12 * (octave - 4) + (chromaticScale.index(self.pitchClass) - chromaticScale.index("A"))


    def __str__(self):
        return str(self.name)


#   Gets the note x semitones above the current note, e.g. A4.getAdjacent(3) would return C5
    def getAdjacent(self, semitones):
        pitchClass = chromaticScale[(chromaticScale.index(self.pitchClass) + semitones) % 12]
        octave     = self.octave + (chromaticScale.index(self.pitchClass) + semitones) // 12
        frequency  = stuttgartPitch * pow(twelthRoot, self.semitonesAboveStuttgart + semitones)

        return Note(pitchClass, octave, frequency)


#   Returns an array of the first 15 overtones as Notes
    def getOvertones(self):
        overtones: list[Note] = []

        for semitonesAbove in overtoneSequence:
            cents      = overtoneSequence[semitonesAbove]
            targetNote = self.getAdjacent(semitonesAbove)

        #   Cents can be thought of as the relative distance between two notes. A4 is 100 cents below A#4,
        #   just as C#1 is 100 cents above C1. If the overtone's exact frequency doesn't fit into equal
        #   temperament, we must retrieve the adjacent note and add the relative distance in cents between
        #   the two notes to determine the exact frequency needed
            if cents != 0:
                direction = -1 if cents < 0 else 1

                adjacentNote   = targetNote.getAdjacent(direction)
                tunedFrequency = targetNote.frequency + (abs((targetNote.frequency - adjacentNote.frequency)) * (cents / 100))

                targetNote = Note(targetNote.pitchClass, targetNote.octave, tunedFrequency)

            overtones.append(targetNote)

        return overtones


#   Returns the aggregate power level of all frequency bins belonging to a note in a buffer analysis
    def getPower(self, buffer):
    #   Get neighbor notes
        noteBelow = self.getAdjacent(-1)
        noteAbove = self.getAdjacent( 1)

    #   Determine the range of frequency bins applicable to this note by finding the frequencies 50 cents below and above
        lowerThreshold = int(math.ceil( self.frequency + (abs((self.frequency - noteBelow.frequency)) * -0.5)))
        upperThreshold = int(math.floor(self.frequency + (abs((self.frequency - noteAbove.frequency)) *  0.5)))

    #   Reduce indices by 1 to compensate for removed DC offset and return result
        lowerIndex = int(round((lowerThreshold - 1) / buffer.binSize, 0))
        upperIndex = int(round((upperThreshold - 1) / buffer.binSize, 0))

        return sum(buffer.analysis[lowerIndex : upperIndex])