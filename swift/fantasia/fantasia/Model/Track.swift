//
//  Track.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift
import AVFoundation
import Accelerate

class Track: Loop {
    //
    // MARK: Persisted values
    //
    
    @Persisted var sourceURL = ""
    @Persisted var section: Section?
    @Persisted var sourceDurationSeconds: Double

    //
    // MARK: Computed values
    //
    
    
    override var sourceAmplitudes : [CGFloat] {
        return computeSourceAmplitudes()
    }
    
    override var sourceStopSeconds : Double {
        return sourceDurationSeconds
    }
    
    override func createPlayer(parent: AVAudioNode) -> Player {
        return TrackPlayer(self, parent: parent)
    }
    
    lazy var audioFile : AVAudioFile = loadAudioFile()
    
    override var format: AVAudioFormat {
        return audioFile.processingFormat
    }
    

    //
    // MARK: STATIC
    //
    

    static func fileDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
    //
    // MARK: Computation
    //
        
    private func computeSourceAmplitudes() -> [CGFloat] {
        let samplesPerAmplitude = Int(sampleRate / Track.AMPLITUDES_PER_SECOND)
        let numberOfAmplitudes = Int(frameCount) / samplesPerAmplitude
        
        var amplitudes = [CGFloat](repeating: 0, count: numberOfAmplitudes)
        
        audioFile.framePosition = 0
        
        let bufferSize = AVAudioFrameCount(samplesPerAmplitude)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: audioFile.processingFormat, frameCapacity: bufferSize) else {
            return amplitudes
        }
        
        let channelCount = Int(format.channelCount)
        
        for i in 0..<numberOfAmplitudes {
            do {
                try audioFile.read(into: buffer)
                
                var sumAmplitude: Float = 0
                
                for channel in 0..<channelCount {
                    if let channelData = buffer.floatChannelData?[channel] {
                        var amplitude: Float = 0
                        vDSP_meamgv(channelData, 1, &amplitude, vDSP_Length(bufferSize))
                        sumAmplitude += amplitude
                    }
                }
                amplitudes[i] = CGFloat(sumAmplitude) * 250 // Scale for visibility
            } catch {
                print("Error reading audio file: \(error)")
                break
            }
        }
        
        return amplitudes
    }
    
    private func loadAudioFile() -> AVAudioFile {
        let audioURL = Track.fileDirectory().appendingPathComponent(sourceURL)
        // TODO: This is meant to be memoized, but we end up getting new versions of the Track object
        // so we're actually loading the audio file over and over.
        // AppLogger.model.debug("Track.audioFile Reading audio file from URL: \(audioURL)")
        do {
            return try AVAudioFile(forReading: audioURL)
        } catch {
            AppLogger.model.error("Track.audioFile Failed to open audio file: \(audioURL)")
            fatalError(error.localizedDescription)
        }
    }
    
  

    // MARK: Initializers
    
    convenience init(name: String, sourceURL: String) {
        self.init()
        self.name = name
        self.sourceURL = sourceURL
        audioFile = loadAudioFile()
        sourceDurationSeconds = Double(audioFile.length) / audioFile.processingFormat.sampleRate
        stopSeconds = sourceDurationSeconds
        AppLogger.model.info("Track.init")
        AppLogger.model.info("Duration (s) \(self.sourceDurationSeconds)")
        AppLogger.model.info("Creating Track: \(name)")
        AppLogger.model.info("URL: \(sourceURL)")
    }

    
    
}



