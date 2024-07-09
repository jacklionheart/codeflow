import SwiftUI
import RealmSwift

struct LoopflowView: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audio: Audio
    @ObservedResults(Track.self, where: { track in track.parent == nil }) var tracks
    @State private var presentedTracks: [Track] = []

    var body: some View {
        NavigationStack(path: $presentedTracks) {
            VStack {
                HStack {
                    Text("Your Tracks")
                        .font(.title).bold().padding(.leading)
                    Spacer()
                }
                List {
                    ForEach(tracks) { track in
                        PlayerView(track:track, trackAudio: audio.audio(for: track),
                                   onEdit: {presentedTracks.append(track)})
                    }
                }.listStyle(PlainListStyle())
                RecorderView(recorder: audio.record)
            }
            .navigationDestination(for: Track.self) { track in
                EditorView(audio: audio, track: track, trackAudio: audio.audio(for: track))
            }
        }
    }
}
