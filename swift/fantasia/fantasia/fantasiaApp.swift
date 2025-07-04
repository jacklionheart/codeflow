//
//  fantasiaApp.swift
//  fantasia
//
//  Created by Jack Heart on 11/18/22.
//

import SwiftUI

@main
struct FantasiaApp: App {
    var session = RealmSession()
    var audio = Audio()

    var body: some Scene {
        WindowGroup {
            FantasiaView().environmentObject(session).environmentObject(audio)
        }
    }
    
}
