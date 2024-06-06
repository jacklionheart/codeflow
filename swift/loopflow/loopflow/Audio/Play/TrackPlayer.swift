//
//  TrackPlayer.swift
//  loopflow
//
//  Created by Jack Heart on 3/27/24.
//

import Foundation
import AVFoundation
import Combine


protocol TrackPlayerInternal {
    func play()
    func stop()

    func updateVolume(_ volume : Float)
}



// TrackPlayer is the object used by views to play, pause, and stop a track.
class TrackPlayer : ObservableObject {
    // MARK: - Member variables
    
    // Initialization parameters
    var track: Track
    var parent: AVAudioNode
    private var audioEngine: AVAudioEngine

    // Observable properties
    @Published var isPlaying: Bool = false

    // Internal implementation
    private var timePitchNode: AVAudioUnitTimePitch
    private var internalPlayer: TrackPlayerInternal
    private var cancellables = Set<AnyCancellable>()
    

    // MARK: - Public Methods

    // Plays a track, pausing any currently playing track.
    // Continues from where last paused, or else the beginning.
    public func play() {
        SingletonPlayer.shared.replace(with: self)
        internalPlayer.play()
        isPlaying = true
    }
    
    
    // Plays a track from the beginning.
    public func start() {
        stop()
        play()
    }
    
    // Stop playing a track and returns to the beginning for future plays.
    public func stop() {
        internalPlayer.stop()
        isPlaying = false
    }
    
 
    // MARK: - Initialization
    //
    
    private func subscribeToChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties): // Correctly access the properties array in the tuple
                for property in properties {
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        // Update the published pitchCents when the property changes
                        DispatchQueue.main.async {
                            self!.internalPlayer.updateVolume(Float(newValue))
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
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        
        timePitchNode = AVAudioUnitTimePitch()
        audioEngine.attach(timePitchNode)
        audioEngine.connect(timePitchNode, to: parent, format: track.format())
        timePitchNode.pitch = Float(track.pitchCents)
        timePitchNode.rate = Float(track.playbackRate)
        
        if track.subtype == .Mix {
            internalPlayer = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            internalPlayer = Take(track, parent: timePitchNode, audioEngine: audioEngine)
        }

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

// SingletonPlayer ensures only one track ever plays at a time.
class SingletonPlayer : ObservableObject {
    static let shared = SingletonPlayer()

    @Published var currentPlayer: TrackPlayer?
    
    public func replace(with trackPlayer: TrackPlayer?) {
        if currentPlayer != nil {
            currentPlayer!.stop()
        }
        currentPlayer = trackPlayer
    }
    
    public func stop() {
        replace(with: nil)
    }
}
