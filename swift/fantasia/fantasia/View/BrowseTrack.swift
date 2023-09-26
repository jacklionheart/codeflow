//
//  ListTrackView.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//

import SwiftUI
import RealmSwift
import AVFoundation

struct BrowseTrack: View {
    @EnvironmentObject var session: Session
    @EnvironmentObject var audioMixer: AudioMixer
    @ObservedRealmObject var track: Track
    @Binding var selected: Track?

    func isSelected() -> Bool {
        if selected == nil {
            return false
        }
        return selected! == track
    }
    
    func select() {
        selected = track
    }
    
    
    var body: some View {
        HStack {
            Text(track.name).onTapGesture {
                select()
            }
            Spacer()
            PlayButton(isPlaying: audioMixer.isPlaying(track), start: {
                print("playing")
                audioMixer.play(track)
            }, stop: {
                audioMixer.stop(track)
            })
        }
        
    }
    
    
    struct PlayButton: View {
        var isPlaying: Bool
        var start: (() -> Void)
        var stop: (() -> Void)
        
        var body: some View {
            Button(action: {
                if isPlaying {
                    stop()
                } else {
                    start()
                }
            }) {
                Image(systemName: isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 40))
                    .foregroundColor(.blue)
            }
        }
    }
}


