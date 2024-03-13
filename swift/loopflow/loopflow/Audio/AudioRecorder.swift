import Foundation
import RealmSwift
import AVFoundation

class AudioRecorder : ObservableObject {
        
    @Published var avAudioRecorder: AVAudioRecorder?
    @Published var currentRecordingPath: URL?
    
    init() {
        avAudioRecorder = nil
        currentRecordingPath = nil
    }
    
    private static func fileDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
    
    private static func newUrl(for date: Date) -> URL {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
        return AudioRecorder.fileDirectory().appendingPathComponent("Loopflow_Recording_\(dateFormatter.string(from: date)).m4a")
    }
    
    var isRecording: Bool {
        return avAudioRecorder != nil
    }
    
    func start() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default)
            try audioSession.setActive(true)
        } catch {
            print("Failed to set up audio session: \(error.localizedDescription)")
        }
        
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        print("start")
        print(isRecording)
        if !isRecording {
            do {
                print("do")
                let date = Date()
                currentRecordingPath = AudioRecorder.newUrl(for: date)
                avAudioRecorder = try AVAudioRecorder.init(url: currentRecordingPath!, settings: settings)
                avAudioRecorder!.record()
                print("recording to \(currentRecordingPath!.absoluteString)")
                print(isRecording)
            } catch let error {
                print("Error starting recorder: \(error.localizedDescription)")
                avAudioRecorder = nil
                currentRecordingPath = nil
            }
        }
    }
    
    func stopAndSave(to: Track?) {
        print("stop")
        if isRecording {
            avAudioRecorder!.stop()
            avAudioRecorder = nil
            
            writeToRealm {
                // TODO: Get realm from session?
                let realm = try! Realm()
                let newTrack = Track(sourceURL: currentRecordingPath!.absoluteString)
                realm.add(newTrack)
                if to != nil {
                    to!.addSubtrack(newTrack)
                }
            }
            
            currentRecordingPath = nil
        }
    }
}
