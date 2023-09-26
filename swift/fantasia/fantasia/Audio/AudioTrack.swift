//
//  AudioTrack.swift
//  fantasia
//
//  Created by Jack Heart on 5/9/23.
//

import Foundation
import AVFoundation

class AudioTrack: ObservableObject {
    
    var track: Track
    var audioEngine: AVAudioEngine?
    var audioLengthSamples: Int64
    var audioSampleRate: Double
    var audioLengthSeconds: Double
    var audioFile: AVAudioFile
    var playerNode: AVAudioPlayerNode
    @Published var isPlaying = false
    
    init(_ track: Track) {
        self.track = track
        
        let file = try! AVAudioFile(forReading: URL(string: track.sourceURL)!)
        let format = file.processingFormat
        
        audioFile = file
        playerNode = AVAudioPlayerNode()
        audioEngine = AVAudioEngine()
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode,
                            to: audioEngine.outputNode,
                            format: audioFile.processingFormat)

        audioEngine.prepare()
        do {
           try audioEngine.start()
        } catch {
            print(error)
        }
    }
    
  
    
    public func play(trak) {
        schedule()
        playerNode.play()
        isPlaying = true
    }
    
    public func stop() {
        playerNode.stop()
        isPlaying = false
    }
    
}
    
