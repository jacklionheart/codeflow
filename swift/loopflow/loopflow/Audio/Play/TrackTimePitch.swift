//
//  TrackPlayable.swift
//  loopflow
//
//  Created by Jack Heart on 4/9/24.
//

import Foundation
import AVFoundation
import Combine

class TrackTimePitch {
    var audioEngine: AVAudioEngine
    var track: Track
    var parent: AVAudioNode
    var timePitchNode: AVAudioUnitTimePitch
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    
    internal func subscribeToChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties): // Correctly access the properties array in the tuple
                for property in properties {
                    if property.name == "pitchCents", let newValue = property.newValue as? Double {
                        DispatchQueue.main.async {
                            self!.timePitchNode.pitch = Float(newValue)
                        }
                    }
                    
                    if property.name == "playbackRate", let newValue = property.newValue as? Double {
                        DispatchQueue.main.async {
                            self!.timePitchNode.rate = Float(newValue)
                        }
                    }
                }
            case .error(let error):
                AppLogger.audio.error("An error occurred: \(error)")
            case .deleted:
                AppLogger.audio.debug("The object was deleted.")
            }
        }

        // Convert the Realm notification token into a Combine cancellable and add it to the set.
        AnyCancellable {
            notificationToken.invalidate()
        }.store(in: &cancellables)
    }
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        
        timePitchNode = AVAudioUnitTimePitch()
        timePitchNode.pitch = Float(track.pitchCents)
        timePitchNode.rate = Float(track.playbackRate)

        audioEngine.attach(timePitchNode)
        audioEngine.connect(timePitchNode, to: parent, format: track.format())

        subscribeToChanges()
    }
    
    deinit {
        // Cancel all subscriptions when this object is being deinitialized
        cancellables.forEach { $0.cancel() }
        audioEngine.detach(timePitchNode)
    }
}
