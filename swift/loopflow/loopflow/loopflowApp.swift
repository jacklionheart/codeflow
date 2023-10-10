//
//  loopflowApp.swift
//  loopflow
//
//  Created by Jack Heart on 11/18/22.
//

import SwiftUI

@main
struct LoopflowApp: App {
    var session = RealmSession()
    var audioMixer = AudioMixer()

    var body: some Scene {
        WindowGroup {
            Loopflow().environmentObject(session).environmentObject(audioMixer)
        }
    }
}
