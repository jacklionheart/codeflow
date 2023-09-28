//
//  AudioRecorder.swift
//  fantasia
//
//  Created by Jack Heart on 2/13/23.
//

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
        return AudioRecorder.fileDirectory().appending(path:"Loopflow Recording \(date.formatted(date: .complete, time: .complete)).m4a")
    }
    
    var isRecording: Bool {
        return avAudioRecorder != nil
    }
    
    func start() {
        print("start")
        print(isRecording)
        if !isRecording {
            do {
                print("do")
                let date = Date()
                currentRecordingPath = AudioRecorder.newUrl(for: date)
                avAudioRecorder = try AVAudioRecorder.init(url: currentRecordingPath!, settings: [:])
                avAudioRecorder!.record()
                print("recording")
                print(isRecording)
            } catch {
                print("catch")
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
            
            transaction {
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
