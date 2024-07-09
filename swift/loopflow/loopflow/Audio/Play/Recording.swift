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
        if playerNode.lastRenderTime == nil {
            return startPosition
        }
        
        let playerTime = playerNode.playerTime(forNodeTime: playerNode.lastRenderTime!)!
        let sampleRate = track.format.sampleRate
        
        return Double(playerTime.sampleTime) / sampleRate + startPosition
    }
    
    // Internal implementation
    private var playerNode: AVAudioPlayerNode
    private var startPosition = 0.0
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
        startPosition = 0.0
        isPlaying = false
    }
    
    func pause() {
        playerNode.pause()
        isPlaying = false
    }
    
    func receiveNewVolume(_ volume : Double) {
        playerNode.volume = Float(volume)
    }
    
    func receiveNewStartSeconds(_ newStart: Double) {
        if isPlaying && newStart > currentPosition {
            stop()
        }
    }
    
    func receiveNewStopSeconds(_ newStop: Double) {
        if isPlaying {
            if newStop <= currentPosition {
                stop()
            }
            if newStop > currentPosition {
                let from = currentPosition
                stop()
                loop(from: from)
            }
        }
    }
    
    // Implementation

    private func loop(from: Double = 0.0) {
        let audioFile = track.audioFile
        let sampleRate = audioFile.processingFormat.sampleRate
        let startFrame = AVAudioFramePosition((track.thaw()!.startSeconds + from) * sampleRate)
        let totalFrames = AVAudioFramePosition(track.thaw()!.stopSeconds * sampleRate) - startFrame
        startPosition = from
        
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
