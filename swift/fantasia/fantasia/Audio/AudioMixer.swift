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
  
    init() {
        audioEngine = AVAudioEngine()
        playerNodes = [:]
        
        // Create and attach the silent player node
        let silentPlayerNode = AVAudioPlayerNode()
        audioEngine.attach(silentPlayerNode)
        // Create a silent buffer
        let silentFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)!
        let silentBuffer = AVAudioPCMBuffer(pcmFormat: silentFormat, frameCapacity: AVAudioFrameCount(silentFormat.sampleRate * 0.5))!
        silentBuffer.frameLength = silentBuffer.frameCapacity
        // Connect the silent player node to the main mixer
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
    
    private func playSilentBuffer(silentPlayerNode : AVAudioPlayerNode, silentBuffer : AVAudioPCMBuffer) {
        // Play the silent buffer in loop
        silentPlayerNode.scheduleBuffer(silentBuffer) {
            self.playSilentBuffer(silentPlayerNode: silentPlayerNode, silentBuffer: silentBuffer)
        }
        silentPlayerNode.play()
    }

    public func play(_ track : Track) {
        self.stop(track)
        let tid = track.id

        let playerNode = AVAudioPlayerNode()
        audioEngine.attach(playerNode)
        print("adding player for \(tid)")
        playerNodes[tid] = playerNode
        let audioFile = try! AVAudioFile(forReading: URL(string: track.sourceURL)!)
        audioEngine.connect(playerNode,
                            to: audioEngine.mainMixerNode,
                            format: audioFile.processingFormat)
        self.schedule(playerNode, from: audioFile)
        playerNode.play()
    }
    
    private func schedule(_ playerNode : AVAudioPlayerNode, from audioFile : AVAudioFile) {
        playerNode.scheduleFile(audioFile, at: nil) {
            self.schedule(playerNode, from: audioFile)
        }
    }
    
    public func stop(_ track : Track) {
        if let playerNode = playerNodes[track.id] {
            playerNode.stop()
            audioEngine.disconnectNodeInput(playerNode)
            audioEngine.detach(playerNode)
            playerNodes[track.id] = nil
        }
    }
    
    public func isPlaying(_ track: Track) -> Bool {
        let tid = track.id
        if let _ = playerNodes[tid] {
            print("found track \(tid)")
            return true
        } else {
            print("no track for \(tid)")
            return false
        }
    }
    
}
