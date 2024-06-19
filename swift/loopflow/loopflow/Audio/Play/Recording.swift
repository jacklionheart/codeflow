import Foundation
import AVFoundation
import Combine

//
//
//
class Recording : TrackPlayer {
    // MARK: - Member variables

    // Initialization paramters
    var track: Track
    var audioEngine: AVAudioEngine
    var parent: AVAudioNode
    
    // Internal implementation
    private var playerNode: AVAudioPlayerNode
    
    // MARK: - Public Methods
    
    public func play() {
        self.loop()
        playerNode.play()
    }
    
    /// Stops a track from playing.
    public func stop() {
        playerNode.pause()
        playerNode.reset()
    }
    
    public func pause() {
        playerNode.stop()
    }

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
               audio.track.take.play
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
    
    func updateVolume(_ volume : Float) {
        playerNode.volume = volume
    }
    
    // MARK: - Initialization
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        playerNode = AVAudioPlayerNode()
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: parent, format: track.format())
        playerNode.volume = Float(track.volume)
    }
    
    deinit {
        audioEngine.disconnectNodeInput(playerNode)
        audioEngine.disconnectNodeOutput(playerNode)
        audioEngine.detach(playerNode)
    }
}
