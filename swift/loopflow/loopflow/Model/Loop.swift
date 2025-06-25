//
//  Mix.swift
//  loopflow
//
//  Created by Jack Heart on 7/23/24.
//

import Foundation
import AVFoundation
import RealmSwift

class Loop: Object, ObjectKeyIdentifiable {
    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var name = ""
    @Persisted var creationDate = Date()
    
    
    // Start time (in seconds).
    @Persisted var startSeconds = 0.0
    // Stop time (in seconds)
    @Persisted var stopSeconds = 0.0
    // Cents of pitch shift (-2400, 2400)
    @Persisted var pitchCents = 0.0
    // How fast to play the the audio as a multiplier
    @Persisted var playbackRate = 1.0
    // How loud to play the volume as as a multiplier
    @Persisted var volume = 1.0
    
    var format: AVAudioFormat {
        fatalError("Abstract format -- subclass must implement")
    }
    
    var sourceAmplitudes: [CGFloat] {
        fatalError("Abstract amplitudes -- subclass must implement")
    }
    
    var sourceStopSeconds: Double {
        fatalError("Abstract defaultStopSeconds -- subclass must implement")
    }
    
    func createPlayer(parent: AVAudioNode) -> Player {
        fatalError("Abstract createPlayer -- subclass must implement")
    }
     
    var sampleRate: Double {
        return self.format.sampleRate
    }
    
    var durationSeconds: Double {
        return stopSeconds - startSeconds
    }
    
    var startFrame: AVAudioFramePosition {
        return AVAudioFramePosition(startSeconds * sampleRate)
    }
    
    var stopFrame: AVAudioFramePosition {
        return AVAudioFramePosition(stopSeconds * sampleRate)
    }
        
    var frameCount: AVAudioFrameCount {
        return AVAudioFrameCount(stopFrame - startFrame)
    }
    
    
    // TODO: Handle long songs
    public static var AMPLITUDES_PER_SECOND = 20.0;
    
    var amplitudes: [CGFloat] {
        let startIndex = Int(startSeconds * Loop.AMPLITUDES_PER_SECOND)
        let endIndex = min(Int(stopSeconds * Loop.AMPLITUDES_PER_SECOND), sourceAmplitudes.count)
        return Array(sourceAmplitudes[startIndex..<endIndex])
    }

    
    public func reset() {
        volume = 1.0
        pitchCents = 0.0
        playbackRate = 1.0
        startSeconds = 0
        stopSeconds = sourceStopSeconds
    }
}
