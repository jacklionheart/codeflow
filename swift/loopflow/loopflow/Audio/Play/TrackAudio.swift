//
//  TrackPlayer.swift
//  loopflow
//
//  Created by Jack Heart on 3/27/24.
//

import Foundation
import AVFoundation
import Combine
import RealmSwift

protocol TrackPlayer {
    func play()
    func stop()

    func updateVolume(_ volume : Float)
}



// TrackAudio is the object used by views to play, pause, and stop a track.
class TrackAudio : ObservableObject {
    // MARK: - Member variables
    
    // Initialization parameters
    var track: Track
    var parent: AVAudioNode
    private var audioEngine: AVAudioEngine

    // Observable properties
    @Published var isPlaying: Bool = false

    // Internal implementation
    private var timePitchNode: AVAudioUnitTimePitch
    private var trackPlayer: TrackPlayer
    private var cancellables = Set<AnyCancellable>()
    

    // MARK: - Public Methods

    // Plays a track, pausing any currently playing track.
    // Continues from where last paused, or else the beginning.
    public func play() {
        trackPlayer.play()
        isPlaying = true
    }
    
    
    // Plays a track from the beginning.
    public func start() {
        stop()
        play()
    }
    
    // Stop playing a track and returns to the beginning for future plays.
    public func stop() {
        trackPlayer.stop()
        isPlaying = false
    }
    
 
    // MARK: - Initialization
    //
    
    private func subscribeToChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties):
                for property in properties {
                   if property.name == "subtracks" {
                        DispatchQueue.main.async {
                            self!.trackPlayer.stop()
                            self!.installTrackPlayer()
                        }
                    }
                    
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        // Update the published pitchCents when the property changes
                        DispatchQueue.main.async {
                            self!.trackPlayer.updateVolume(Float(newValue))
                        }
                    }

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
                AppLogger.audio.debug("An error occurred: \(error)")
            case .deleted:
                AppLogger.audio.debug("The object was deleted.")
            }
        }

        AnyCancellable {
            notificationToken.invalidate()
        }.store(in: &cancellables)
    }
    
    func installTrackPlayer() {
        AppLogger.audio.debug("Reinstalling trackplayer for \(self.track.name).")
        AppLogger.audio.debug("Num subtracks \(self.track.subtracks.count).")

        track = track.thaw()!.freeze()
        
        audioEngine.disconnectNodeInput(timePitchNode)
        audioEngine.disconnectNodeOutput(timePitchNode)
        audioEngine.detach(timePitchNode)
        audioEngine.attach(timePitchNode)
        
        

        if track.subtype == .Mix {
            trackPlayer = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            trackPlayer = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
        }

        audioEngine.connect(timePitchNode, to: parent, format: track.format())
    }
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        AppLogger.audio.debug("Creating trackPlayer for \(track.name)")
        
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        
        timePitchNode = AVAudioUnitTimePitch()
        audioEngine.attach(timePitchNode)
        timePitchNode.pitch = Float(track.pitchCents)
        timePitchNode.rate = Float(track.playbackRate)

        if track.subtype == .Mix {
            trackPlayer = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            trackPlayer = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
        }
        
        // Connect nodes in a bottom up order
        audioEngine.connect(timePitchNode, to: parent, format: track.format())

        subscribeToChanges()
    }
    
    deinit {
        stop()
        
        audioEngine.disconnectNodeInput(timePitchNode)
        audioEngine.disconnectNodeOutput(timePitchNode)
        audioEngine.detach(timePitchNode)

        cancellables.forEach { $0.cancel() }
    }
}
