//
//  TrackPlayer.swift
//  fantasia
//
//  Created by Jack Heart on 7/30/24.
//

import Foundation
import AVFoundation


class TrackPlayer : Player {
    
    // MARK: - Member variables
    
    // Initialization paramters
    var track: Track
    
    
    override internal func computeCurrentPosition() -> Double {
        if !playerNode.isPlaying || playerNode.lastRenderTime == nil {
            return 0.0
        }
        
        let sampleTime = playerNode.playerTime(forNodeTime: playerNode.lastRenderTime!)!.sampleTime
        let sampleRate = track.format.sampleRate
        let totalSecs = Double(sampleTime) / sampleRate
        let result = totalSecs.truncatingRemainder(dividingBy: track.thaw()!.durationSeconds)
        
//        AppLogger.audio.debug("""
//            Recording.currentPosition
//            sampleTime: \(sampleTime)
//            sampleRate: \(sampleRate)
//            totalSecs: \(totalSecs)
//            loops: \(totalSecs/self.track.thaw()!.durationSeconds)
//            result: \(result)
//        """)
        
        return result
    }
    
    // Internal implementation
    private var playerNode: AVAudioPlayerNode
    private var playerStartPosition  = 0.0
    private var isSegmentScheduled = false

    // MARK: - Methods
    
//    func schedule(at: AVAudioTime?, durationSeconds: Double?) {
//        if !isSegmentScheduled {
//            self.loop(at: at, durationSeconds: durationSeconds)
//            isSegmentScheduled = true
//        }
//    }
//    
//    func playScheduled() {
//        assert(isSegmentScheduled)
//        playerNode.play()
//        isPlaying = true
//    }
//    
//    
    override public func play() {
        super.play()
        if !isSegmentScheduled {
            self.loop()
        }
        playerNode.play()
        isPlaying = true
    }
//    
//    /// Stops a track from playing.
    override public func stop() {
        super.stop()
        playerNode.stop()
        isSegmentScheduled = false
        isPlaying = false
    }
    
    override public func pause() {
        super.pause()
        playerNode.pause()
        isPlaying = false
    }
    
    func receiveNewVolume(_ volume : Double) {
        playerNode.volume = Float(volume)
    }
    
    // Implementation
 
    private func loop(numLoops: Int = 0, at: AVAudioTime? = nil) {
        let liveTrack = track.thaw()!

        
        AppLogger.audio.info("""
            Looping \(liveTrack.name)
            sampleRate: \(liveTrack.sampleRate)
            startFrame: \(liveTrack.startFrame)
            totalFrames: \(liveTrack.frameCount)
            totalSeconds: \(liveTrack.durationSeconds)
            fileFormatSampleRate: \(liveTrack.audioFile.fileFormat.sampleRate)
            processingFormatSampleRate: \(liveTrack.audioFile.processingFormat.sampleRate)
            sampleRate: \(liveTrack.sampleRate)
            currentPosition: \(self.currentPosition)
            currentSamples : \(self.currentPosition * liveTrack.sampleRate)
            durationSeconds: \(self.track.durationSeconds)
            ”
        """)
        
        
        playerNode.scheduleSegment(liveTrack.audioFile, startingFrame: liveTrack.startFrame, frameCount: liveTrack.frameCount, at: at) {
            if numLoops != 1 {
                // TODO: account for playback rate, including of parents
                self.loop(numLoops: numLoops-1, at: nil)
            }
        }
    }

    
    // MARK: - Initialization and deinitialization
    
    init(_ track: Track, parent: AVAudioNode) {
        self.track = track
        playerNode = AVAudioPlayerNode()

        super.init(track, parent: parent)

        engine.attach(playerNode)
        engine.connect(playerNode, to: timePitchNode, format: track.format)

    }
    
    deinit {
        stop()

        engine.disconnectNodeInput(playerNode)
        engine.disconnectNodeOutput(playerNode)
        engine.detach(playerNode)
    }
}


