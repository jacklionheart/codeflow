//
//  AudioMixer.swift
//  fantasia
//
//  Created by Jack Heart on 9/24/23.
//

import Foundation
import AVFoundation

class AudioMixer: ObservableObject {
    var audioEngine: AVAudioEngine
    @Published var playerNodes: [UInt64: AVAudioPlayerNode]
    @Published var activePlayerNodes: [UInt64: AVAudioPlayerNode]
    
    // MARK: - Public Methods
    
    /// Plays a track. Stop all other tracks. Restarts the track from beginning if already playing.
    public func play(_ track : Track) {
        let audioFile = try! AVAudioFile(forReading: URL(string: track.sourceURL)!)
        let playerNode = playerNode(track)
        
        stopAllTracks()
        self.loop(playerNode, from: audioFile)
        playerNode.play()
        activePlayerNodes[track.id] = playerNode
    }
    
    /// Stops a track from playing.
    public func stop(_ track : Track) {
        if let playerNode = activePlayerNodes[track.id] {
            playerNode.stop()
            activePlayerNodes[track.id] = nil
       }
    }
    
    /// Stops all tracks from playing.
    public func stopAllTracks() {
        for (_, playerNode) in activePlayerNodes {
            playerNode.stop()
        }
        activePlayerNodes.removeAll()
    }
    
    /// Returns True iff a track is actively playing.
    public func isPlaying(_ track: Track) -> Bool {
        return activePlayerNodes[track.id] != nil
    }
    
    // MARK: - Initialization

    init() {
        audioEngine = AVAudioEngine()
        playerNodes = [:]
        activePlayerNodes = [:]

        // A Silent Buffer is a hack to avoid an empty engine which can cause problems.
        let silentPlayerNode = AVAudioPlayerNode()
        audioEngine.attach(silentPlayerNode)
        let silentFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)!
        let silentBuffer = AVAudioPCMBuffer(pcmFormat: silentFormat, frameCapacity: AVAudioFrameCount(silentFormat.sampleRate * 0.5))!
        silentBuffer.frameLength = silentBuffer.frameCapacity
        audioEngine.connect(silentPlayerNode, to: audioEngine.mainMixerNode, format: silentBuffer.format)
        audioEngine.connect(audioEngine.mainMixerNode, to: audioEngine.outputNode, format: nil)

        do {
            try AVAudioSession.sharedInstance().setCategory(.playback)
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Error setting up audio session: \(error)")
        }

        do {
            try audioEngine.start()
            playSilentBuffer(silentPlayerNode: silentPlayerNode, silentBuffer: silentBuffer)
        } catch {
            print(error)
        }
    }
    
    // MARK: - Private Methods
    
    private func playSilentBuffer(silentPlayerNode : AVAudioPlayerNode, silentBuffer : AVAudioPCMBuffer) {
        // Play the silent buffer in loop
        silentPlayerNode.scheduleBuffer(silentBuffer) {
            self.playSilentBuffer(silentPlayerNode: silentPlayerNode, silentBuffer: silentBuffer)
        }
        silentPlayerNode.play()
    }
    
    /// Loops a track by scheduling it to
    private func loop(_ playerNode : AVAudioPlayerNode, from audioFile : AVAudioFile) {
        playerNode.scheduleFile(audioFile, at: nil) {
            self.loop(playerNode, from: audioFile)
        }
    }
    private func playerNode(_ track : Track) -> AVAudioPlayerNode {
        let audioFile = try! AVAudioFile(forReading: URL(string: track.sourceURL)!)
        let tid = track.id
        if playerNodes[tid] == nil {
            let playerNode = AVAudioPlayerNode()
            audioEngine.attach(playerNode)
            print("adding player for \(tid)")
            playerNodes[tid] = playerNode
            audioEngine.connect(playerNode,
                                to: audioEngine.mainMixerNode,
                                format: audioFile.processingFormat)
        }
        return playerNodes[tid]!
    }
    
}
