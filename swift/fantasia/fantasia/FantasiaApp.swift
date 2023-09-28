//
//  FantasiaApp.swift
//  fantasia
//
//  Created by Jack Heart on 11/18/22.
//

import SwiftUI

@main
struct FantasiaApp: App {
    var session = RealmSession()
    var audioMixer = AudioMixer()

    var body: some Scene {
        WindowGroup {
            Fantasia().environmentObject(session).environmentObject(audioMixer)
        }
    }
}
