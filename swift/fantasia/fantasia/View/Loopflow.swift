import SwiftUI
import RealmSwift

struct Loopflow: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audioMixer: AudioMixer

    @ObservedResults(Track.self) var tracks

    @State var selected: Track?

    
    func isSelected(_ track: Track) -> Bool {
        if selected == nil {
            return false
        }
        return selected! == track
    }
    
    var body: some View {
        VStack{
            List {
                ForEach(tracks) { track in
                    BrowseTrack(track: track, selected: $selected)
                }
            }
            RecordTrack()
        }
    }

}
