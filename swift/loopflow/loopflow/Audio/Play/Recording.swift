import Foundation
import AVFoundation
import Combine


class Recording : TrackAudioNode {
    
    // MARK: - Member variables
    
    // Initialization paramters
    var track: Track
    var audioEngine: AVAudioEngine
    var parent: AVAudioNode
    
    // Observable properties
    private(set) var isPlaying = false
    
    
    var currentPosition : Double {
        if !playerNode.isPlaying || playerNode.lastRenderTime == nil {
            return 0.0
        }
        
        let sampleTime = playerNode.playerTime(forNodeTime: playerNode.lastRenderTime!)!.sampleTime
        let sampleRate = track.format.sampleRate
        let totalSecs = Double(sampleTime) / sampleRate
        let result = totalSecs.truncatingRemainder(dividingBy: track.thaw()!.durationSeconds)
        
        AppLogger.audio.debug("""
            Recording.currentPosition
            sampleTime: \(sampleTime)
            sampleRate: \(sampleRate)
            totalSecs: \(totalSecs)
            result: \(result)
        """)
        
        return result
    }
    
    // Internal implementation
    private var playerNode: AVAudioPlayerNode
    private var playerStartPosition  = 0.0
    private var isSegmentScheduled = false

    // MARK: - Methods
    
    func play() {
        if !isSegmentScheduled {
            self.loop()
        }
        playerNode.play()
        isPlaying = true
    }
    
    /// Stops a track from playing.
    func stop() {
        playerNode.stop()
        isSegmentScheduled = false
        isPlaying = false
    }
    
    func pause() {
        playerNode.pause()
        isPlaying = false
    }
    
    func receiveNewVolume(_ volume : Double) {
        playerNode.volume = Float(volume)
    }
    
    // Implementation

    private func loop() {
        let audioFile = track.audioFile
        let sampleRate = audioFile.processingFormat.sampleRate
        let startFrame = AVAudioFramePosition((track.thaw()!.startSeconds) * sampleRate)
        let totalFrames = AVAudioFramePosition(track.thaw()!.stopSeconds * sampleRate) - startFrame
        let totalSeconds = track.durationSeconds

        AppLogger.audio.info("""
            Looping \(self.track.name)
            sampleRate: \(sampleRate)
            startFrame: \(startFrame)
            totalFrames: \(totalFrames)
            totalSeconds: \(totalSeconds)
            currentPosition: \(self.currentPosition)
            currentSamples : \(self.currentPosition * sampleRate)
        """)
        
        playerNode.scheduleSegment(audioFile, startingFrame: startFrame, frameCount: AVAudioFrameCount(totalFrames), at: nil) {
            self.loop()
        }
    }

    
    // MARK: - Initialization and deinitialization
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        playerNode = AVAudioPlayerNode()
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: parent, format: track.format)
        playerNode.volume = Float(track.volume)
    }
    
    deinit {
        audioEngine.disconnectNodeInput(playerNode)
        audioEngine.disconnectNodeOutput(playerNode)
        audioEngine.detach(playerNode)
    }
}
