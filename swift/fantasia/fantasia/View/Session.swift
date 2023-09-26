//
//  ViewState.swift
//  fantasia
//
//  Created by Jack Heart on 5/8/23.
//

import SwiftUI
import RealmSwift
import AVFoundation

// Our observable object class
class Session: ObservableObject {
    var realm: Realm
    var audioMixer: AudioMixer
    // let playSession = AVAudioSession.sharedInstance()
    
    init() {
        try! FileManager.default.removeItem(at: Realm.Configuration.defaultConfiguration.fileURL!)
        let configuration = Realm.Configuration(deleteRealmIfMigrationNeeded: true)
        realm = try! Realm(configuration: configuration)
        audioMixer = AudioMixer()
     }

}
