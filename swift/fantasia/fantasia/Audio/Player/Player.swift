//
//  Player.swift
//  fantasia
//
//  Created by Jack Heart on 7/30/24.
//

import Foundation
import Combine
import AVFoundation
////  is the object used by views to play, pause, and stop a track.
//class  : ObservableObject {
//    // MARK: - Member variables
//    
//    // Initialization parameters
//    var track: Track
//    var parent: AVAudioNode
//    private var audioEngine: AVAudioEngine
//    
//    // Observable properties
//    @Published var isPlaying: Bool = false
//    @Published var currentPosition: Double = 0
//    
//    // Internal implementation
//    private var timePitchNode: AVAudioUnitTimePitch
//    private var inputNode: Node
//    private var cancellables = Set<AnyCancellable>()
//    private var positionUpdateTimer: Timer?
//
//    
//    // MARK: - Public Methods
//    
//    func schedule(at: AVAudioTime?, durationSeconds: Double?) {
//        inputNode.schedule(at: at, durationSeconds: durationSeconds)
//    }
//
//    // Plays a track, pausing any currently playing track.
//    // Continues from where last paused, or else the beginning.
//    public func play() {
//        inputNode.play()
//        startPositionUpdates()
//        isPlaying = true
//    }
//    
//    // Stop playing a track and returns to the beginning for future plays.
//    public func pause() {
//        inputNode.pause()
//        stopPositionUpdates()
//        isPlaying = false
//    }
//    
//    public func stop() {
//        inputNode.stop()
//        stopPositionUpdates()
//        currentPosition = 0.0
//        isPlaying = false
//    }
//    
//    // Plays a track from the beginning.
//    public func start() {
//        stop()
//        play()
//    }
//    
//    
//    // Schedule a mix for play in the future
//    public func scheduleAt(at: AVAudioTime, ) {
//        inputNode.play()
//        startPositionUpdates()
//        isPlaying = true
//    }
//    
//    // MARK: - Implementation
//    
//    private func startPositionUpdates() {
//        positionUpdateTimer = Timer.scheduledTimer(withTimeInterval: 0.016, repeats: true) { [weak self] _ in
//            guard let self = self else { return }
//            self.currentPosition = self.inputNode.currentPosition
//        }
//    }
//    
//    private func stopPositionUpdates() {
//        positionUpdateTimer?.invalidate()
//        positionUpdateTimer = nil
//    }
//   
//    // MARK: - Initialization
//    //
//    
//    private func subscribeToTrackChanges() {
//        let notificationToken = track.thaw()!.observe { [weak self] change in
//            switch change {
//            case .change(_, let properties):
//                for property in properties {
//                   if property.name == "subtracks" {
//                        DispatchQueue.main.async {
//                            self!.inputNode.stop()
//                            self!.installTrackPlayer()
//                        }
//                    }
//                    
//                    if property.name == "startSeconds" || property.name == "stopSeconds" {
//                        DispatchQueue.main.async {
//                            self!.stop()
//                        }
//                    }
//                    
//                    if property.name == "volume", let newValue = property.newValue as? Double {
//                        DispatchQueue.main.async {
//                            self!.inputNode.receiveNewVolume(newValue)
//                        }
//                    }
//
//                    if property.name == "pitchCents", let newValue = property.newValue as? Double {
//                        DispatchQueue.main.async {
//                            self!.timePitchNode.pitch = Float(newValue)
//                        }
//                    }
//                    
//                    if property.name == "playbackRate", let newValue = property.newValue as? Double {
//                        DispatchQueue.main.async {
//                            self!.timePitchNode.rate = Float(newValue)
//                        }
//                    }
//                }
//            case .error(let error):
//                AppLogger.audio.debug("An error occurred: \(error)")
//            case .deleted:
//                AppLogger.audio.debug("The object was deleted.")
//            }
//        }
//
//        AnyCancellable {
//            notificationToken.invalidate()
//        }.store(in: &cancellables)
//    }
//    
//    
//    private func forwardTrackChanges() {
//        // Propagate any changes to any @Persisted property in Track to observers of
//        track.thaw()!.objectWillChange.sink { [weak self] _ in
//            self?.objectWillChange.send()
//        }.store(in: &cancellables)
//    }
//
//    
//    func installTrackPlayer() {
//        // TODO: do we need to do all this?
//        AppLogger.audio.debug("Reinstalling trackplayer for \(self.track.name).")
//        AppLogger.audio.debug("Num subtracks \(self.track.subtracks.count).")
//
//        track = track.thaw()!.freeze()
//        
//        audioEngine.disconnectNodeInput(timePitchNode)
//        audioEngine.disconnectNodeOutput(timePitchNode)
//        audioEngine.detach(timePitchNode)
//        audioEngine.attach(timePitchNode)
//        
//        if track.subtype == .Mix {
//            inputNode = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
//        } else {
//            assert(track.subtype == .Recording)
//            inputNode = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
//        }
//
//        audioEngine.connect(timePitchNode, to: parent, format: track.format)
//    }
//        
//    
//    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
//        AppLogger.audio.debug("Creating trackPlayer for \(track.name)")
//        
//        self.track = track
//        self.parent = parent
//        self.audioEngine = audioEngine
//        
//        timePitchNode = AVAudioUnitTimePitch()
//        audioEngine.attach(timePitchNode)
//        timePitchNode.pitch = Float(track.pitchCents)
//        timePitchNode.rate = Float(track.playbackRate)
//
//        if track.subtype == .Mix {
//            inputNode = Mix(track, parent: timePitchNode, audioEngine: audioEngine)
//        } else {
//            assert(track.subtype == .Recording)
//            inputNode = Recording(track, parent: timePitchNode, audioEngine: audioEngine)
//        }
//        
//        // Connect nodes in a bottom up order
//        audioEngine.connect(timePitchNode, to: parent, format: track.format)
//        
//        subscribeToTrackChanges()
//    }
//    
//    deinit {
//        stop()
//        
//        audioEngine.disconnectNodeInput(timePitchNode)
//        audioEngine.disconnectNodeOutput(timePitchNode)
//        audioEngine.detach(timePitchNode)
//
//        cancellables.forEach { $0.cancel() }
//    }
//}

class Player : ObservableObject, Identifiable, Equatable {
    
    static func == (lhs: Player, rhs: Player) -> Bool {
        return lhs.id == rhs.id
    }
    
    var engine: AVAudioEngine
    var parent: AVAudioNode
    var loop : Loop

    // Observable properties
    @Published public internal(set) var isPlaying = false
    @Published public internal(set) var currentPosition = 0.0

    // Internal implementation
    internal var timePitchNode: AVAudioUnitTimePitch
    internal var cancellables = Set<AnyCancellable>()
    internal var positionUpdateTimer: Timer?

    
    public var id : UInt64 {
        return loop.id
    }
    
    // Plays a track, pausing any currently playing track.
    // Continues from where last paused, or else the beginning.
    public func play() {
        startPositionUpdates()
        isPlaying = true
    }
    
    // Stop playing a track and returns to the beginning for future plays.
    public func pause() {
        stopPositionUpdates()
        isPlaying = false
    }
    
    public func stop() {
        stopPositionUpdates()
        currentPosition = 0.0
        isPlaying = false
    }
    
    // Plays a track from the beginning.
    public func start() {
        stop()
        play()
    }
    
    private func startPositionUpdates() {
        positionUpdateTimer = Timer.scheduledTimer(withTimeInterval: 0.016, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.currentPosition = computeCurrentPosition()
        }
    }
    
    private func stopPositionUpdates() {
        positionUpdateTimer?.invalidate()
        positionUpdateTimer = nil
    }
    
    private func receiveNewVolume(_ volume: Double) {
        fatalError("Abstract receieveNewVolume -- subclass must implement receiveNewVolume")
    }
    
    internal func computeCurrentPosition() -> Double {
        fatalError("subclass must implement computeCurrentPosition")
    }
    
    private func subscribeToLoop() {
        let notificationToken = loop.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties):
                for property in properties {
                    if property.name == "startSeconds" || property.name == "stopSeconds" {
                        DispatchQueue.main.async {
                            self!.stop()
                        }
                    }
                    
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        DispatchQueue.main.async {
                            self!.receiveNewVolume(newValue)
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
    
    private func forwardLoopChanges() {
           // Propagate any changes to any @Persisted property in Track to observers of
           loop.thaw()!.objectWillChange.sink { [weak self] _ in
               self?.objectWillChange.send()
           }.store(in: &cancellables)
       }

        init(_ loop: Loop, parent: AVAudioNode) {
            AppLogger.audio.debug("Creating Player for \(loop.name)")
            
            self.loop = loop
            self.parent = parent
            self.engine = parent.engine!
            
            timePitchNode = AVAudioUnitTimePitch()
            engine.attach(timePitchNode)
            timePitchNode.pitch = Float(loop.pitchCents)
            timePitchNode.rate = Float(loop.playbackRate)
            
            engine.connect(timePitchNode, to: parent, format: loop.format)
            
            subscribeToLoop()
            forwardLoopChanges()
        }
        
        deinit {
            engine.disconnectNodeInput(timePitchNode)
            engine.disconnectNodeOutput(timePitchNode)
            engine.detach(timePitchNode)

            cancellables.forEach { $0.cancel() }
        }
}
