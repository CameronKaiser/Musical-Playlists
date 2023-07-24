import App
import Analyzer
import pymongo
from pymongo import MongoClient
import multiprocessing
from multiprocessing import Pool
from math import ceil

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Insert your MongoDB credential here
mongo = MongoClient("mongodb+srv://{credential}.mongodb.net/")

cores      = multiprocessing.cpu_count()     # Number of cores to be used in multiprocessing
directory  = "Insert training data folder here"
genre      = "Orchestral"                    # Genre attributed to the Configuration
iterations = 1000

def main():

    database = mongo.MusicalPlaylists
    tunings  = database.Tunings
    cursor   = database.Tracks.find()

#   Get all tracks from database to serve as a key for the machine learner
    trackDocuments = {}
    for track in cursor:
        trackDocuments[track["track"]] = {  "startingKey"         : track["startingKey"],
                                            "closingKey"          : track["closingKey"],
                                            "startingRelativeKey" : track.get("startingRelativeKey", None),
                                            "closingRelativeKey"  : track.get("closingRelativeKey",  None)  }

#   Generate a random configuration to analyze tracks and upload results to database
    for x in range(iterations):

        tracks = App.getPlaylist(directory)
        configuration = Analyzer.Configuration()

    #   Add configuration and genre to each track so they can be accessed by App.py
        for track in tracks:
            track.configuration = configuration
            track.genre         = genre

    #   Determine how many tracks should be processed by each core
        chunkSize = int(ceil(len(tracks) / cores))

    #   Analyse tracks using multiprocessing
        pool = Pool(processes = cores)
        analyzedTracks = pool.map(App.analyzeTrack, tracks, chunkSize)
        pool.close()

    #   Check each track analysis against our key to determine score of configuration
        score = 0
        for track in analyzedTracks:
            trackDocument = trackDocuments[track.name]

            if ((track.startKey.tonic == trackDocument["startingKey"] or track.startKey.tonic == trackDocument["startingRelativeKey"])
            and (track.endKey.tonic   == trackDocument["closingKey"]  or track.endKey.tonic   == trackDocument["closingRelativeKey"])):
                score += 1

        score = round(score / len(tracks), 4) * 100

    #   Upload configuration and score to our database
        tuningDocument = {"score"        : score,
                          "genre"        : genre,
                          "coefficients" : configuration.toDictionary()}

        tunings.insert_one(tuningDocument)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()



