//
//  TrackPlayer.swift
//  loopflow
//
//  Created by Jack Heart on 3/27/24.
//

import Foundation
import AVFoundation

protocol Playable {
    func play()
    func stop()
    var track: Track { get }
}

struct TrackPlayer {
    static func Create(_ track: Track, parent: AVAudioNode,  audioEngine: AVAudioEngine) -> Playable {
        if track.subtype == .Mix {
            return Mix(track, parent: parent, audioEngine: audioEngine)
//        } else if track.subtype == .Sequence {
//            return Sequence(track, parent: parent, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            return Take(track, parent: parent, audioEngine: audioEngine)
        }
    }
}
