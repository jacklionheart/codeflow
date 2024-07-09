import Foundation
import RealmSwift
import AVFoundation
import os.log

class Recorder : ObservableObject {
    var audioEngine: AVAudioEngine
    public var trackManager: TrackSingleton

    @Published var avAudioRecorder: AVAudioRecorder?
    @Published var currentRecordingPath: URL?
    @Published public var name: String
    @Published var elapsedTime: TimeInterval = 0
    private var startTime: Date?
    private var timer: Timer?

    init(audioEngine: AVAudioEngine, trackManager: TrackSingleton) {
        self.audioEngine = audioEngine
        self.trackManager = trackManager
        avAudioRecorder = nil
        name = ""
        currentRecordingPath = nil
        currentRecordingPath = nil
    }
    
    
    private static func newUrl(for date: Date) -> URL {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
        return Track.fileDirectory().appendingPathComponent("Loopflow_Recording_\(dateFormatter.string(from: date)).m4a")
    }
    
    var active: Bool {
        return avAudioRecorder != nil
    }
    
    func start() {
        
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 2,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        AppLogger.audio.debug("audio.record.start active:\(self.active)")
        if !active {
            do {
                let date = Date()
                currentRecordingPath = Recorder.newUrl(for: date)
                avAudioRecorder = try AVAudioRecorder.init(url: currentRecordingPath!, settings: settings)
                startTime = Date()
                avAudioRecorder!.record()
 //                waveform.startMonitoring()
                elapsedTime = 0
                timer = Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { [weak self] _ in
                    self?.updateElapsedTime()
                }
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
  //          waveform.stopMonitoring()
            trackManager.stop()
            timer = nil
            startTime = nil
            elapsedTime = 0
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
                let newTrack = Track(name: name, sourceURL: currentRecordingPath!.lastPathComponent)
                realm.add(newTrack)
                if to != nil {
                    to!.thaw()!.addSubtrack(newTrack)
                }
            }
            
            currentRecordingPath = nil
        }
    }
    
    private func updateElapsedTime() {
          guard let startTime = startTime else { return }
          elapsedTime = Date().timeIntervalSince(startTime)
   }
}

//class RecorderWaveform: ObservableObject {
//    private var audioEngine: AVAudioEngine
//    private let bufferSize = 1024
//    private let amplitudeCount = 200
//    private var circularBuffer: [CGFloat]
//    private var currentIndex = 0
//
//    @Published var amplitudes: [CGFloat] = Array(repeating: 0, count: 200)
//    private var amplitudesNeedUpdate = false
//
//    init(_ audioEngine: AVAudioEngine) {
//        self.audioEngine =  audioEngine
//        self.circularBuffer = Array(repeating: 0, count: amplitudeCount)
//    }
//
//    func startMonitoring() {
//        let input = audioEngine.inputNode
//        let format = input.outputFormat(forBus: 0)
//        AppLogger.audio.debug("record.start installing tap")
//        input.installTap(onBus: 0, bufferSize: UInt32(bufferSize), format: format) { [weak self] buffer, _ in
//            self?.processBuffer(buffer: buffer)
//        }
//    }
//
//    func stopMonitoring() {
//        audioEngine.inputNode.removeTap(onBus: 0)
//    }
//
//
//    private func processBuffer(buffer: AVAudioPCMBuffer) {
//        print("processing buffer")
//        guard let channelData = buffer.floatChannelData?[0] else { return }
//        print("got past guard")
//        let frameCount = Int(buffer.frameLength)
//        
//        let samplesPerAmplitude = frameCount / amplitudeCount
//        
//        for i in 0..<amplitudeCount {
//            let startSample = i * samplesPerAmplitude
//            let endSample = min((i + 1) * samplesPerAmplitude, frameCount)
//            var sum: Float = 0
//            
//            for j in startSample..<endSample {
//                sum += abs(channelData[j])
//            }
//            
//            let newAmplitude = CGFloat(sum / Float(endSample - startSample)) * 50 // Scale for visibility
//            if circularBuffer[currentIndex] != newAmplitude {
//                circularBuffer[currentIndex] = newAmplitude
//                amplitudesNeedUpdate = true
//            }
//            currentIndex = (currentIndex + 1) % amplitudeCount
//        }
//
//        if amplitudesNeedUpdate {
//            DispatchQueue.main.async {
//                self.updateAmplitudes()
//            }
//        }
//    }
//
//    private func updateAmplitudes() {
//        for i in 0..<amplitudeCount {
//            let index = (currentIndex + i) % amplitudeCount
//            amplitudes[i] = circularBuffer[index]
//        }
//        amplitudesNeedUpdate = false
//        print(amplitudes)
//        objectWillChange.send()
//    }
//}

