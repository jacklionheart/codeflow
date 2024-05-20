import SwiftUI
import RealmSwift
import AVFoundation

struct EditorView: View {
    @EnvironmentObject var session: RealmSession
    @ObservedObject var audio: Audio
    @ObservedRealmObject var track: Track
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        VStack {
            HStack {
                Button(action: {
                    presentationMode.wrappedValue.dismiss()
                }) {
                    Image(systemName: "chevron.left")
                        .font(.title)
                }
                Text(track.name)
                    .font(.title).bold().padding(.leading)
                Spacer()
            }
            VStack(alignment: .leading) {
                Text(track.name).bold()
                HStack {
                    Text(Format.date(track.creationDate))
                    Spacer()
                    Text(Format.duration(track.durationSeconds))
                }.foregroundColor(.gray)
                HStack {
                    PlayButton(player: audio.play, track: track)
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
                                TimeView(track:subtrack)
                            }
                        }
                    }
                }
            }

            Spacer()
            RecorderView(recorder: audio.record, player:audio.play, parent: track)
        }
    }
}
