//
//  TrackManager.swift
//  loopflow
//
//  Created by Jack Heart on 6/11/24.
//

import Foundation
import AVFoundation

class TrackSingleton : ObservableObject {
    var audioEngine: AVAudioEngine
    
    @Published public var currentAudio: TrackAudio?
    
    private var audioCache: [UInt64: TrackAudio] = [:]
    
    func audio(for track: Track) -> TrackAudio {
        if let cachedAudio = audioCache[track.id] {
            return cachedAudio
        } else {
            let audio = TrackAudio(track, parent: audioEngine.mainMixerNode, audioEngine: audioEngine)
            audioCache[track.id] = audio
            return audio
        }
    }
    
    func pause() {
        if currentAudio != nil {
            currentAudio!.pause()
            currentAudio = nil
        }
    }
    
    func stop() {
        if currentAudio != nil {
            currentAudio!.stop()
            currentAudio = nil
        }
    }
    
    func play(_ trackAudio : TrackAudio) {
        pause()
        currentAudio = trackAudio
        trackAudio.play()
    }
    
    init(audioEngine: AVAudioEngine) {
        self.audioEngine = audioEngine
    }
}
