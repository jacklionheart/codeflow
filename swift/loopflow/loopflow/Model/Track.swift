//
//  Track.swift
//  loopflow
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift
import AVFoundation
import Accelerate

class Track: Object, ObjectKeyIdentifiable {
    
    // MARK: Subtypes
    
    public enum Subtype: String {
        case Recording
        case Mix
        case Sequence
    }

    // MARK: Persisted values

    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var name = ""
    @Persisted var creationDate = Date()
    // Start time (in seconds).
    @Persisted var startSeconds = 0.0
    // Stop time (in seconds)
    @Persisted var stopSeconds = 0.0
    @Persisted var sourceDurationSeconds = 0.0

    // Cents of pitch shift (-2400, 2400)
    @Persisted var pitchCents = 0.0

    @Persisted var playbackRate = 1.0
    @Persisted var sourceURL = ""
    @Persisted var subtracks = RealmSwift.List<Track>()
    @Persisted var parent: Track?
    @Persisted var creator: Person?
    @Persisted var volume = 1.0
    @Persisted var subtypeRaw = Subtype.Recording.rawValue
    
    // MARK: Computed values
    
    lazy var sourceAmplitudes : [CGFloat] = computeSourceAmplitudes()
    lazy var audioFile : AVAudioFile = loadAudioFile()
    
    var format: AVAudioFormat {
            if subtype == .Recording {
                return audioFile.processingFormat
            } else {
                assert(subtype == .Mix)
                assert(subtracks.count > 0)
                return subtracks[0].format
        }
    }
    
    var durationSeconds: Double {
        return stopSeconds - startSeconds
    }
    
    var amplitudes: [CGFloat] {
        let startIndex = Int(startSeconds * Track.AMPLITUDES_PER_SECOND)
        let endIndex = min(Int(stopSeconds * Track.AMPLITUDES_PER_SECOND), sourceAmplitudes.count)
        return Array(sourceAmplitudes[startIndex..<endIndex])
    }

        
    // MARK: Initializers
    
    convenience init(name: String, sourceURL: String) {
        self.init()
        self.name = name
        self.sourceURL = sourceURL
        audioFile = loadAudioFile()
        sourceDurationSeconds = Double(audioFile.length) / audioFile.fileFormat.sampleRate
        stopSeconds = sourceDurationSeconds
        AppLogger.model.info("Track.init")
        AppLogger.model.info("Duration (s) \(self.sourceDurationSeconds)")
        AppLogger.model.info("Creating Track: \(name)")
        AppLogger.model.info("URL: \(sourceURL)")
    }
    
    // MARK: Audio-facing API
    
    // `subtype` determines the behavior a track object in the UX.
    // An alternative design would have been to use inheritance between
    // different objects.
    // However, Realm support for object inheritance is somewhat limited,
    // and so sharing a single Object type creates more freedom at the database
    // level.
    //
    var subtype: Subtype {
        get {
            return Subtype(rawValue: subtypeRaw) ?? .Recording
        }
        set {
            subtypeRaw = newValue.rawValue
        }
    }
    
    // `convertToMix` converts a Recording-type track
    // to an Mix by making a new subtrack which is a copy of this track,
    // and then converting this track into an Mix type.
    public func convertToMix() {
        assert(subtype == .Recording)

        let newTrack = createCopy()
        subtype = .Mix
        addSubtrack(newTrack)
        sourceURL = ""
        resetMix()
    }
    
    public func addSubtrack(_ subtrack: Track) {
        assert(subtrack.parent == nil)
        if subtype == Subtype.Recording {
            self.convertToMix()
        }
        
        subtracks.append(subtrack)
        subtrack.parent = self
    }
    
    public func resetMix() {
        volume = 1.0
        pitchCents = 0.0
        playbackRate = 1.0
        startSeconds = 0
        stopSeconds = sourceDurationSeconds
    }
    
    public static var AMPLITUDES_PER_SECOND = 20.0;
    private func computeSourceAmplitudes() -> [CGFloat] {
        let avAudioFile = audioFile
        let sampleRate = avAudioFile.fileFormat.sampleRate
        let samplesPerAmplitude = Int(sampleRate / Track.AMPLITUDES_PER_SECOND)
        let totalFrames = AVAudioFramePosition(sourceDurationSeconds * sampleRate)
        let numberOfAmplitudes = Int(totalFrames) / samplesPerAmplitude
        
        var amplitudes = [CGFloat](repeating: 0, count: numberOfAmplitudes)
        
        avAudioFile.framePosition = 0
        
        let bufferSize = AVAudioFrameCount(samplesPerAmplitude)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: avAudioFile.processingFormat, frameCapacity: bufferSize) else {
            return amplitudes
        }
        
        for i in 0..<numberOfAmplitudes {
            do {
                try avAudioFile.read(into: buffer)
                
                if let channelData = buffer.floatChannelData?[0] {
                    var amplitude: Float = 0
                    vDSP_maxmgv(channelData, 1, &amplitude, vDSP_Length(bufferSize))
                    amplitudes[i] = CGFloat(amplitude) * 250 // Scale for visibility
                }
            } catch {
                print("Error reading audio file: \(error)")
                break
            }
        }
        
        return amplitudes
    }

    public func loadAudioFile() -> AVAudioFile {
        assert(subtype == Subtype.Recording)
        
        let audioURL = Track.fileDirectory().appendingPathComponent(sourceURL)
        AppLogger.model.debug("Track.audioFile Reading audio file from URL: \(audioURL)")
        do {
            return try AVAudioFile(forReading: audioURL)
        } catch {
            AppLogger.model.error("Track.audioFile Failed to open audio file: \(error.localizedDescription)")
            fatalError(error.localizedDescription)
        }
    }

    // MARK: Private Manipulation
 
    private func createCopy() -> Track {
        assert(subtype == .Recording)
        let newTrack = Track()
        newTrack.name = name
        newTrack.creationDate = creationDate
        newTrack.creator = creator
        newTrack.sourceURL = sourceURL
        newTrack.sourceDurationSeconds = sourceDurationSeconds
        newTrack.volume = volume
        newTrack.pitchCents = pitchCents
        // parent is not copied
        return newTrack
    }
    
    //
    // MARK: STATIC
    //
    
    static func fileDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
}



