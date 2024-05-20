//
//  AudioPlayer.swift
//  loopflow
//
//  Created by Jack Heart on 3/25/24.
//

import Foundation
import AVFoundation

class Player : ObservableObject {
    var engine: AVAudioEngine
    @Published var playable: Playable?

    public func start(_ track : Track) {
        stop()
        playable = TrackPlayer.Create(track, parent: engine.mainMixerNode, audioEngine: engine)
        playable!.play()
    }
    
    public func stop() {
        if playable != nil {
            playable!.stop()
        }
        playable = nil
    }
    
    public func isPlaying(_ track : Track) -> Bool {
        if playable != nil {
            return playable!.track.id == track.id
        }
        return false
    }
    
    init(_ engine : AVAudioEngine) {
        self.engine = engine
    }
}


