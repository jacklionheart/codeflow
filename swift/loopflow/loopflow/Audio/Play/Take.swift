import Foundation
import AVFoundation
import Combine

//
//
//
class Take : Playable {
    var audioEngine: AVAudioEngine
    public var track: Track
    var playerNode: AVAudioPlayerNode
    var trackTimePitch: TrackTimePitch
    var parent: AVAudioNode
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Public Methods
    
    public func play() {
        self.loop()
        playerNode.play()
    }
    
    /// Stops a track from playing.
    public func stop() {
        playerNode.stop()
    }

    // MARK: - Initialization

/// Loops a track by scheduling it to
    private func loop() {
        let audioFile = track.audioFile()
        let sampleRate = audioFile.processingFormat.sampleRate
        let startSample = AVAudioFramePosition(track.startSeconds * sampleRate)
        let endSample = AVAudioFramePosition((track.startSeconds + track.durationSeconds) * sampleRate)
        let frameCount = AVAudioFrameCount(endSample - startSample)
        let trackURL = track.sourceURL
        let trackName = track.name

        AppLogger.audio.info("""
               audio.track.play
               --- Playing track ---
               Track name: \(trackName)
               Track location: \(trackURL)
               Sample Rate: \(sampleRate)
               Start Sample: \(startSample)
               End Sample: \(endSample)
               Frame Count: \(frameCount)
               -------------------------------
               """)
        
        playerNode.scheduleSegment(audioFile, startingFrame: startSample, frameCount: frameCount, at: nil) {
            self.loop()
        }
    }
    
    private func cleanup() {
        audioEngine.detach(playerNode)
    }

    private func subscribeToChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties): // Correctly access the properties array in the tuple
                for property in properties {
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        // Update the published pitchCents when the property changes
                        DispatchQueue.main.async {
                            self!.playerNode.volume = Float(newValue)
                        }
                    }

                }
            case .error(let error):
                AppLogger.audio.debug("An error occurred: \(error)")
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
        self.audioEngine = audioEngine
        self.parent = parent
        playerNode = AVAudioPlayerNode()
        playerNode.volume = Float(track.volume)
        trackTimePitch = TrackTimePitch(track, parent: parent, audioEngine: audioEngine)
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: trackTimePitch.timePitchNode, format: track.format())
        subscribeToChanges()
    }
    
    deinit {
        // Cancel all subscriptions when this object is being deinitialized
        cancellables.forEach { $0.cancel() }
        cleanup()
    }
}
