import random

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

chromaticScale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

selfRange        = (  1, 2)
domRange         = (0.0, 0.7)
domSubRange      = (0.5, 1.5)
minorRange       = (  0, 0.25)
majorRange       = (  0, 0.25)
triadicRange     = (  1, 2)
leadingToneRange = (0.5, 1)
tritoneRange     = ( -5, 0)
phrygianRange    = ( -5, 0)
diatonicRange    = (  1, 2)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Configuration:

    #   The Configuration object is a set of coefficients that are used to analyze a track's key. If no parameters are
    #   included, a random configuration within the ranges above will be created

        def __init__(self, input = None):
            if isinstance(input, dict):
                self.selfCoefficient        = input.selfCoefficient
                self.domCoefficient         = input.domCoefficient
                self.domSubCoefficient      = input.domSubCoefficient
                self.minorCoefficient       = input.minorCoefficient
                self.majorCoefficient       = input.majorCoefficient
                self.triadicCoefficient     = input.triadicCoefficient
                self.leadingToneCoefficient = input.leadingToneCoefficient
                self.tritoneCoefficient     = input.tritoneCoefficient
                self.phrygianCoefficient    = input.phrygianCoefficient
                self.diatonicCoefficient    = input.diatonicCoefficient
            else:
                if isinstance(input, str) and input == "Orchestral":
                    self.selfCoefficient        =  1.98
                    self.domCoefficient         =  0.05
                    self.domSubCoefficient      =  1.45
                    self.minorCoefficient       =  0.02
                    self.majorCoefficient       =  0.19
                    self.triadicCoefficient     =  1.44
                    self.leadingToneCoefficient =  0.74
                    self.tritoneCoefficient     = -4.35
                    self.phrygianCoefficient    = -3.34
                    self.diatonicCoefficient    =  1.23
                else:
                #   No parameter means the configuration will be generated randomly
                    self.selfCoefficient        = random.uniform(selfRange          [0], selfRange          [1])
                    self.domCoefficient         = random.uniform(domRange           [0], domRange           [1])
                    self.domSubCoefficient      = random.uniform(domSubRange        [0], domSubRange        [1])
                    self.minorCoefficient       = random.uniform(minorRange         [0], minorRange         [1])
                    self.majorCoefficient       = random.uniform(majorRange         [0], majorRange         [1])
                    self.triadicCoefficient     = random.uniform(triadicRange       [0], triadicRange       [1])
                    self.leadingToneCoefficient = random.uniform(leadingToneRange   [0], leadingToneRange   [1])
                    self.tritoneCoefficient     = random.uniform(tritoneRange       [0], tritoneRange       [1])
                    self.phrygianCoefficient    = random.uniform(phrygianRange      [0], phrygianRange      [1])
                    self.diatonicCoefficient    = random.uniform(diatonicRange      [0], diatonicRange      [1])


        def toDictionary(self):
            return {"selfCoefficient"        : round(self.selfCoefficient       , 2),
                    "domCoefficient"         : round(self.domCoefficient        , 2),
                    "domSubCoefficient"      : round(self.domSubCoefficient     , 2),
                    "minorCoefficient"       : round(self.minorCoefficient      , 2),
                    "majorCoefficient"       : round(self.majorCoefficient      , 2),
                    "triadicCoefficient"     : round(self.triadicCoefficient    , 2),
                    "leadingToneCoefficient" : round(self.leadingToneCoefficient, 2),
                    "tritoneCoefficient"     : round(self.tritoneCoefficient    , 2),
                    "phrygianCoefficient"    : round(self.phrygianCoefficient   , 2),
                    "diatonicCoefficient"    : round(self.diatonicCoefficient   , 2)}

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TonalityScorer:

    #   Scoring tool used to analyze the key of a track. Uses coefficients from a configuration to grade the
    #   various harmonic relationships relative to the key being scored

        def __init__(self, notes, note, configuration):
            self.note             = note
            self.noteIndex        = chromaticScale.index(note)
            self.unison           = notes[note]
            self.minorSecondBelow = notes[chromaticScale[(self.noteIndex - 1) % 12]]
            self.minorSecondAbove = notes[chromaticScale[(self.noteIndex + 1) % 12]]
            self.majorSecondAbove = notes[chromaticScale[(self.noteIndex + 2) % 12]]
            self.majorSecondBelow = notes[chromaticScale[(self.noteIndex - 2) % 12]]
            self.minorThirdAbove  = notes[chromaticScale[(self.noteIndex + 3) % 12]]
            self.minorThirdBelow  = notes[chromaticScale[(self.noteIndex - 3) % 12]]
            self.majorThirdBelow  = notes[chromaticScale[(self.noteIndex - 4) % 12]]
            self.majorThirdAbove  = notes[chromaticScale[(self.noteIndex + 4) % 12]]
            self.fourthAbove      = notes[chromaticScale[(self.noteIndex + 5) % 12]]
            self.tritoneAbove     = notes[chromaticScale[(self.noteIndex + 6) % 12]]
            self.fifthAbove       = notes[chromaticScale[(self.noteIndex + 7) % 12]]
            self.notes            = notes
            self.principalPower   = max(list(notes.values()))
            self.configuration    = configuration

    #   Unison relationship
        def significance(self):
            return self.unison / self.principalPower

    #   Dominant - Tonic relationship
        def dominantRelationship(self):
            return self.configuration.domCoefficient * (self.fifthAbove / self.principalPower)

    #   Dominant - Tonic - Subdominant relationship
        def dominantSubdominantRelationship(self):
            return self.configuration.domSubCoefficient * (((self.fourthAbove + self.fifthAbove) / 2) / self.principalPower)

    #   Relative Keys relationship (minor)
        def minorRelativeRelationship(self):
            return self.configuration.minorCoefficient * ((self.minorThirdBelow - self.minorThirdAbove) / self.principalPower)

    #   Relative Keys relationship (major)
        def majorRelativeRelationship(self):
            return self.configuration.majorCoefficient * ((self.minorThirdAbove - self.minorThirdBelow) / self.principalPower)

    #   Triadic relationship (e.g. C E G)
        def triadicRelationship(self):
            return self.configuration.triadicCoefficient * ((self.unison + (self.minorThirdAbove + self.majorThirdAbove) + self.fifthAbove) / 3) / self.principalPower

    #   Leading Tone relationship (special case for minor leading tone)
        def leadingToneRelationship(self):
            if self.majorSecondBelow > self.minorSecondBelow:
                return (self.minorSecondBelow + self.majorSecondBelow) * (min(self.majorSecondBelow, self.minorSecondBelow) / max(self.majorSecondBelow, self.minorSecondBelow)) / self.principalPower
            else:
                return self.configuration.leadingToneCoefficient * (self.minorSecondBelow / self.principalPower)

    #   Tritone counter-relationship
        def tritoneRelationship(self):
            return self.configuration.tritoneCoefficient * (self.tritoneAbove / self.principalPower)

    #   Phrygian counter-relationship
        def phrygianRelationship(self):
            return self.configuration.phrygianCoefficient * (self.minorSecondAbove / self.principalPower)

    #   Diatonic Relationship
        def diatonicRelationship(self):
            minorRelationship = ((self.unison
                                + self.majorSecondAbove
                                + self.minorThirdAbove
                                + self.fourthAbove
                                + self.fifthAbove
                                + self.majorThirdBelow
                                + self.majorSecondBelow) / 7) / self.principalPower

            majorRelationship = ((self.unison
                                + self.majorSecondAbove
                                + self.majorThirdAbove
                                + self.fourthAbove
                                + self.fifthAbove
                                + self.minorThirdBelow
                                + self.minorSecondBelow) / 7) / self.principalPower

            if minorRelationship > majorRelationship:
                return minorRelationship * self.configuration.diatonicCoefficient
            else:
                return majorRelationship * self.configuration.diatonicCoefficient
