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
        case Group
        case Sequence
    }

    // MARK: Persisted values

    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var name = Object.randomName()
    @Persisted var creationDate = Date()
    // Start time into the source, in seconds.
    @Persisted var startSeconds = 0.0
    // Duration past start-time to play, in seconds.
    @Persisted var durationSeconds = 0.0

    @Persisted var sourceURL = ""
    @Persisted var subtracks = RealmSwift.List<Track>()
    @Persisted var parent: Track?
    @Persisted var creator: Creator?
    @Persisted var volume = 1.0
    @Persisted var subtypeRaw = Subtype.Recording.rawValue

    // MARK: Initializers
    
    convenience init(sourceURL: String) {
        self.init()
        self.sourceURL = sourceURL
        print("Creating Track: \(name)")
        print("URL: \(sourceURL)")
        durationSeconds = audioFile().duration
        print("Duration (s) \(durationSeconds)")
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
    
    // `convertToArrangement` converts a Recording-type track
    // to an Arrangment by making a new subtrack which is a copy of this track,
    // and then converting this track into an Arrangement type.
    public func convertToGroup() {
        assert(subtype == .Recording)

        let newTrack = createCopy()
        subtype = .Group
        subtracks.append(newTrack)
        sourceURL = ""
        resetMix()
        denormalize()
    }
    
    public func addSubtrack(_ subtrack: Track) {
        assert(subtrack.parent == nil)
        if subtype == Subtype.Recording {
            convertToGroup()
        }
        
        subtracks.append(subtrack)
        subtrack.parent = self
        denormalize()

    }
    
    public func resetMix() {
        volume = 1.0
    }
    
    public func audioFile() -> AVAudioFile {
        return try! AVAudioFile(forReading: URL(string: sourceURL)!)
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
        // parent is not copied
        
        newTrack.denormalize()
        
        return newTrack
    }
        
    // `denormalize` stores derived data from subtracks onto the track.
    private func denormalize() {
        if subtype == .Group {
            if subtracks.count == 0 {
                durationSeconds = 0
            } else {
                durationSeconds = subtracks.map({ $0.durationSeconds }).max()!
            }
        }
    }
}



