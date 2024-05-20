import SwiftUI
import RealmSwift

struct LoopflowView: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audio: Audio
    @ObservedResults(Track.self, where: { track in track.parent == nil }) var tracks
    @State private var selectedTrack: Track?
    
    var body: some View {
        VStack {
            HStack {
                Text("Your Tracks")
                    .font(.title).bold().padding(.leading)
                Spacer()
            }
            List {
                ForEach(tracks) { track in
                    PlayerView(player: audio.play, track: track, onEdit: {
                        selectedTrack = track
                    })
                }
            }.listStyle(PlainListStyle())
            RecorderView(recorder: audio.record, player:audio.play)
        }
        .sheet(item: $selectedTrack) { track in
            EditorView(audio: audio, track: track)
        }
    }
}
