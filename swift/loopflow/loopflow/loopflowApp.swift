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
    var audio = Audio()

    var body: some Scene {
        WindowGroup {
            LoopflowView().environmentObject(session).environmentObject(audio)
        }
    }
    
}
