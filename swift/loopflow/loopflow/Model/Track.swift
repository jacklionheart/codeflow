//
//  Track.swift
//  loopflow
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift
import AVFoundation

class Track: Object, ObjectKeyIdentifiable {
    
    // MARK: Subtypes
    
    public enum Subtype: String {
        case Recording
        case Mix
        case Sequence
    }

    // MARK: Persisted values

    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var name = ""
    @Persisted var creationDate = Date()
    // Start time into the source, in seconds.
    @Persisted var startSeconds = 0.0
    // Duration past start-time to play, in seconds.
    @Persisted var durationSeconds = 0.0
    // Cents of pitch shift (-2400, 2400)
    @Persisted var pitchCents = 0.0
    @Persisted var playbackRate = 1.0
    @Persisted var sourceURL = ""
    @Persisted var subtracks = RealmSwift.List<Track>()
    @Persisted var parent: Track?
    @Persisted var creator: Person?
    @Persisted var volume = 1.0
    @Persisted var subtypeRaw = Subtype.Recording.rawValue

    // MARK: Initializers
    
    convenience init(name: String, sourceURL: String) {
        self.init()
        self.name = name
        self.sourceURL = sourceURL
        let af = audioFile()
        durationSeconds = Double(af.length) / af.fileFormat.sampleRate
        AppLogger.model.info("Track.init")
        AppLogger.model.info("Duration (s) \(self.durationSeconds)")
        AppLogger.model.info("Creating Track: \(name)")
        AppLogger.model.info("URL: \(sourceURL)")
    }
    
    // MARK: Audio-facing API
    
    // `subtype` determines the behavior a track object in the UX.
    // An alternative design would have been to use inheritance between
    // different objects.
    // However, Realm support for object inheritance is somewhat limited,
    // and so sharing a single Object type creates more freedom at the database
    // level.
    //
    var subtype: Subtype {
        get {
            return Subtype(rawValue: subtypeRaw) ?? .Recording
        }
        set {
            subtypeRaw = newValue.rawValue
        }
    }
    
    // `convertToMix` converts a Recording-type track
    // to an Mix by making a new subtrack which is a copy of this track,
    // and then converting this track into an Mix type.
    public func convertToMix() {
        assert(subtype == .Recording)

        let newTrack = createCopy()
        subtype = .Mix
        addSubtrack(newTrack)
        sourceURL = ""
        resetMix()
        denormalize()
    }
    
    public func addSubtrack(_ subtrack: Track) {
        assert(subtrack.parent == nil)
        if subtype == Subtype.Recording {
            self.convertToMix()
        }
        
        subtracks.append(subtrack)
        subtrack.parent = self
        denormalize()

    }
    
    public func resetMix() {
        volume = 1.0
        pitchCents = 0.0
        playbackRate = 1.0
    }
    
    public func audioFile() -> AVAudioFile {
        assert(subtype == Subtype.Recording)
        
        let audioURL = Track.fileDirectory().appendingPathComponent(sourceURL)
        AppLogger.model.debug("Track.audioFile Reading audio file from URL: \(audioURL)")
        do {
            return try AVAudioFile(forReading: audioURL)
        } catch {
            AppLogger.model.error("Track.audioFile Failed to open audio file: \(error.localizedDescription)")
            fatalError(error.localizedDescription)
        }
    }
    
    public func format() -> AVAudioFormat {
        if subtype == .Recording {
            return audioFile().processingFormat
        } else {
            assert(subtype == .Mix)
            assert(subtracks.count > 0)
            return subtracks[0].format()
        }
    }
        
    // MARK: Private Manipulation
 
    private func createCopy() -> Track {
        assert(subtype == .Recording)
        let newTrack = Track()
        newTrack.name = name
        newTrack.creationDate = creationDate
        newTrack.creator = creator
        newTrack.sourceURL = sourceURL
        newTrack.durationSeconds = durationSeconds
        newTrack.volume = volume
        newTrack.pitchCents = pitchCents
        // parent is not copied
        
        newTrack.denormalize()
        
        return newTrack
    }
        
    // `denormalize` stores derived data from subtracks onto the track.
    private func denormalize() {
        if subtype == .Mix {
            if subtracks.count == 0 {
                durationSeconds = 0
            } else {
                durationSeconds = subtracks.map({ $0.durationSeconds }).max()!
            }
        }
    }
    
    //
    // MARK: STATIC
    //
    
    static func fileDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
}



