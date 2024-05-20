import Foundation
import RealmSwift
import AVFoundation
import os.log

class Recorder : ObservableObject {
        
    @Published var avAudioRecorder: AVAudioRecorder?
    @Published var currentRecordingPath: URL?
    @Published public var name: String
    
    init() {
        avAudioRecorder = nil
        name = ""
        currentRecordingPath = nil
    }
    
    private static func fileDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
    
    private static func newUrl(for date: Date) -> URL {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
        return Recorder.fileDirectory().appendingPathComponent("Loopflow_Recording_\(dateFormatter.string(from: date)).m4a")
    }
    
    var active: Bool {
        return avAudioRecorder != nil
    }
    
    func start() {
        
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        AppLogger.audio.debug("audio.record.start active:\(self.active)")
        if !active {
            do {
                let date = Date()
                currentRecordingPath = Recorder.newUrl(for: date)
                avAudioRecorder = try AVAudioRecorder.init(url: currentRecordingPath!, settings: settings)
                avAudioRecorder!.record()
                name = Object.randomName()
                AppLogger.audio.debug("audio.record.start recording to \(self.currentRecordingPath!.absoluteString) active:\(self.active)")
            } catch let error {
                AppLogger.audio.error("audio.record.start Error starting recorder: \(error.localizedDescription)")
                avAudioRecorder = nil
                currentRecordingPath = nil
            }
        }
    }
    
    func stop(to: Track?) {
        AppLogger.audio.info("audio.record.stop active:\(self.active) to:\(to)")
        if active {
            avAudioRecorder!.stop()
            do {
                let fileManager = FileManager.default
                let attributes = try fileManager.attributesOfItem(atPath: currentRecordingPath!.path)
                if let fileSize = attributes[.size] as? NSNumber {
                    AppLogger.audio.info("audio.record.stop File size: \(fileSize) bytes")
                } else {
                    AppLogger.audio.error("audio.record.stop Could not retrieve file size.")
                }
            } catch {
                AppLogger.audio.error("audio.record.stop Error getting \(self.currentRecordingPath!.absoluteString) file attributes: \(error.localizedDescription)")
            }
            
            avAudioRecorder = nil
            
            writeToRealm {
                // TODO: Get realm from session?
                let realm = try! Realm()
                let newTrack = Track(name: name, sourceURL: currentRecordingPath!.path)
                realm.add(newTrack)
                if to != nil {
                    to!.thaw()!.addSubtrack(newTrack)
                }
            }
            
            currentRecordingPath = nil
        }
    }
}



