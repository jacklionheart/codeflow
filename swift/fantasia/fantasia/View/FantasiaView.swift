import SwiftUI
import RealmSwift

struct FantasiaView: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audio: Audio
    @ObservedResults(Section.self) var sections
    @State private var presentedSections: [Section] = []

    var body: some View {
//        NavigationStack(path: $presentedTracks) {
            VStack {
                HStack {
                    Text("Your Tracks")
                        .font(.title).bold().padding(.leading)
                    Spacer()
                }
                List {
                    ForEach(sections) { section in
                        PlayerView(player: audio.player(for: section.tracks[0]))
//                                   onEdit: {presentedTracks.append(section)})
                    }
                }.listStyle(PlainListStyle())
                RecorderView(recorder: audio.record)
            }
//            .navigationDestination(for: Section.self) { track in
//                EditorView(audio: audio, section: section, player: audio.audio(for: section))
//            }
//        }
    }
}
