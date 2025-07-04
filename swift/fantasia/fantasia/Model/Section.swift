//
//  Section.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift
import AVFoundation
import Accelerate

// A section is made up of 0 or more tracks. Each track is played concurrently to comprise the section.
// The first track is considered the base track. All other tracks are called
// layers. When looping, if a layer is longer than a base track,
// it will loop at the next repeat of the base track.
// If a layer is shorter than the base track, it loop the maximum number of times it can before the base track finishes, then restart once the
// base track repeats.
class Section: Loop {
    
    @Persisted var tracks = RealmSwift.List<Track>()
    @Persisted var song: Song?
    
    // MARK: Computed values
    
    override var format: AVAudioFormat {
        // TODO: Do we need to consider possibly different formats?
        return tracks[0].format
    }
    
    override var sourceAmplitudes : [CGFloat] {
        // TODO: Add together amplitudes (including looping tracks)
        return tracks[0].sourceAmplitudes
    }
    
    override var sourceStopSeconds : Double {
        return tracks.reduce(into: 0.0) { result, track in
            // TODO: this consider when base track and loop tracks don't line up quite right
            result = max(result, track.durationSeconds)
        }
    }
    
    override func createPlayer(parent: AVAudioNode) -> Player {
        return SectionPlayer(self, parent: parent)
    }
        
    // MARK: Public API
        
    public func addTrack(_ track: Track) {
        tracks.append(track)
        track.section = self
        
        // TODO: stopSeconds
    }
    

    
    // MARK: Initializers
    
    convenience init(name: String) {
        self.init()
        self.name = name
    }
    
    
    
}



