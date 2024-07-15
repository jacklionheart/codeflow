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
import Accelerate

protocol TrackAudioNode {
    var currentPosition: Double { get }

    func play()
    func pause()
    func stop()
    func receiveNewVolume(_ volume : Double)
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
    @Published var currentPosition: Double = 0
    
    // Internal implementation
    private var timePitchNode: AVAudioUnitTimePitch
    private var inputNode: TrackAudioNode
    private var cancellables = Set<AnyCancellable>()
    private var positionUpdateTimer: Timer?

    
    // MARK: - Public Methods
    
    // Plays a track, pausing any currently playing track.
    // Continues from where last paused, or else the beginning.
    public func play() {
        inputNode.play()
        startPositionUpdates()
        isPlaying = true
    }
    
    // Stop playing a track and returns to the beginning for future plays.
    public func pause() {
        inputNode.pause()
        stopPositionUpdates()
        isPlaying = false
    }
    
    public func stop() {
        inputNode.stop()
        stopPositionUpdates()
        currentPosition = 0.0
        isPlaying = false
    }
    
    // Plays a track from the beginning.
    public func start() {
        stop()
        play()
    }
    
    // MARK: - Implementation
    
    private func startPositionUpdates() {
        positionUpdateTimer = Timer.scheduledTimer(withTimeInterval: 0.016, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.currentPosition = self.inputNode.currentPosition
        }
    }
    
    private func stopPositionUpdates() {
        positionUpdateTimer?.invalidate()
        positionUpdateTimer = nil
    }
   
    // MARK: - Initialization
    //
    
    private func subscribeToTrackChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties):
                for property in properties {
                   if property.name == "subtracks" {
                        DispatchQueue.main.async {
                            self!.inputNode.stop()
                            self!.installTrackPlayer()
                        }
                    }
                    
                    if property.name == "startSeconds" || property.name == "stopSeconds" {
                        DispatchQueue.main.async {
                            self!.stop()
                        }
                    }
                    
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        DispatchQueue.main.async {
                            self!.inputNode.receiveNewVolume(newValue)
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
    
    
    private func forwardTrackChanges() {
        // Propagate any changes to any @Persisted property in Track to observers of TrackAudio
        track.thaw()!.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }.store(in: &cancellables)
    }

    
    func installTrackPlayer() {
        // TODO: do we need to do all this?
        AppLogger.audio.debug("Reinstalling trackplayer for \(self.track.name).")
        AppLogger.audio.debug("Num subtracks \(self.track.subtracks.count).")

        track = track.thaw()!.freeze()
        
        audioEngine.disconnectNodeInput(timePitchNode)
        audioEngine.disconnectNodeOutput(timePitchNode)
        audioEngine.detach(timePitchNode)
        audioEngine.attach(timePitchNode)
        
        if track.subtype == .Mix {
            inputNode = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            inputNode = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
        }

        audioEngine.connect(timePitchNode, to: parent, format: track.format)
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
            inputNode = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
        } else {
            assert(track.subtype == .Recording)
            inputNode = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
        }
        
        // Connect nodes in a bottom up order
        audioEngine.connect(timePitchNode, to: parent, format: track.format)
        
        subscribeToTrackChanges()
    }
    
    deinit {
        stop()
        
        audioEngine.disconnectNodeInput(timePitchNode)
        audioEngine.disconnectNodeOutput(timePitchNode)
        audioEngine.detach(timePitchNode)

        cancellables.forEach { $0.cancel() }
    }
}
