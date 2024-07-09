import SwiftUI
import RealmSwift
import AVFoundation

struct EditorView: View {
    @EnvironmentObject var session: RealmSession
    @ObservedObject var audio: Audio
    @ObservedRealmObject var track: Track
    @ObservedObject var trackAudio: TrackAudio

    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        VStack {
            VStack(alignment: .leading) {
                Text(track.name).bold()
                HStack {
                    Text(Format.date(track.creationDate))
                    Spacer()
                    Text(Format.duration(track.durationSeconds))
                }.foregroundColor(.gray)
                HStack {
                    PlayButton(trackAudio: trackAudio, track: track)
                }
            }
            VStack(alignment: .leading) {
                if track.subtype == .Recording {
                    Text("single track")
                } else {
                    List {
                        ForEach(track.subtracks) { subtrack in
                            VStack{
                                Text(subtrack.name).bold()
                            }
                        }
                    }.listStyle(PlainListStyle())
                }
            }

            Spacer()
            RecorderView(recorder: audio.record, parent: track)
        }
    }
}
