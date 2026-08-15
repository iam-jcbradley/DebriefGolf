import { Document, Page, StyleSheet, Text, View } from "@react-pdf/renderer";
import type { Combine, RoundAnalytics, RoundShotAnalytics, RoundSummary, SGCategory } from "@/lib/api";

const CATEGORY_LABELS: Record<SGCategory, string> = {
  OTT: "Off the Tee",
  APP: "Approach",
  ARG: "Around the Green",
  PUTT: "Putting",
};

const CATEGORY_ORDER: SGCategory[] = ["OTT", "APP", "ARG", "PUTT"];

const styles = StyleSheet.create({
  page: { padding: 36, fontSize: 10, fontFamily: "Helvetica", color: "#211d17" },
  title: { fontSize: 20, marginBottom: 2 },
  subtitle: { fontSize: 11, color: "#726a5a", marginBottom: 16 },
  sectionTitle: {
    fontSize: 12,
    marginTop: 14,
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: 1,
    color: "#28402f",
  },
  row: { flexDirection: "row", marginBottom: 3 },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  statTile: {
    width: "48%",
    borderWidth: 1,
    borderColor: "#ded2b4",
    padding: 8,
    marginBottom: 8,
  },
  statLabel: { fontSize: 8, color: "#726a5a", textTransform: "uppercase", letterSpacing: 0.5 },
  statValue: { fontSize: 16, marginTop: 2 },
  leakLabel: { width: "60%" },
  leakValue: { width: "40%", textAlign: "right" },
  bullet: { marginBottom: 6 },
  bulletTitle: { fontSize: 11, marginBottom: 2 },
  bulletBody: { fontSize: 9, color: "#3a3226" },
  bulletMeta: { fontSize: 8, color: "#726a5a", marginTop: 2 },
  footer: { position: "absolute", bottom: 24, left: 36, right: 36, fontSize: 8, color: "#726a5a" },
});

function formatSigned(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

// "unclassified" (app/services/approach.py's ApproachLeave) covers every
// shot the classifier doesn't consider a missed-green recovery attempt at
// all — tee shots, putts, fairway lies, penalty markers — so it isn't a
// "strike pattern" a coach could act on. Only the three classifications
// that describe an actual approach outcome belong in this section.
const STRIKE_PATTERN_LABELS: Record<string, string> = {
  on_green: "Hit the green",
  safe_leave: "Missed, safe leave",
  short_sided: "Missed, short-sided",
};

function strikePatternSummary(shots: RoundShotAnalytics[]): { label: string; count: number }[] {
  const counts: Record<string, number> = {};
  for (const shot of shots) {
    if (shot.approach_leave === "unclassified") continue;
    counts[shot.approach_leave] = (counts[shot.approach_leave] ?? 0) + 1;
  }
  return Object.entries(counts).map(([key, count]) => ({
    label: STRIKE_PATTERN_LABELS[key] ?? key,
    count,
  }));
}

// react-pdf's built-in Helvetica uses WinAnsi encoding, which doesn't cover
// ≥/± /° — those render as garbled glyphs (a stray "e" for ≥) instead of
// throwing, so this has to be caught by eye, not a type error. Combine
// target metrics (app/services/practice_combines.py) use those characters
// for the on-screen Practice Hub UI, which has no such limitation — only
// the PDF's copy needs sanitizing.
function pdfSafeText(text: string): string {
  return text.replace(/≥/g, ">=").replace(/±/g, "+/-").replace(/°/g, " deg");
}

export interface CoachBriefDocumentProps {
  round: RoundSummary;
  analytics: RoundAnalytics;
  combines: Combine[];
}

/** 1-Page "Coach-Ready" Lesson Brief (PRD §7.2, §10 Phase 6): net stroke
 * leaks (Strokes Gained, worst category first), strike patterns (approach
 * shot outcomes), Tiger 5 metrics, and a recommended coaching agenda
 * (the same weakness -> combine mapping the Practice Hub shows, so what a
 * coach sees here matches what the player is already being told to work
 * on — see app/services/practice_combines.py).
 */
export function CoachBriefDocument({ round, analytics, combines }: CoachBriefDocumentProps) {
  const worstFirst = [...CATEGORY_ORDER].sort(
    (a, b) => analytics.strokes_gained.by_category[a] - analytics.strokes_gained.by_category[b]
  );
  const strikePatterns = strikePatternSummary(analytics.shots);

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        <Text style={styles.title}>Debrief Golf — Coach-Ready Lesson Brief</Text>
        <Text style={styles.subtitle}>
          Round #{round.id} · {new Date(round.played_at).toLocaleDateString()} · Score{" "}
          {round.total_score ?? "—"} · Handicap bucket {analytics.handicap_bucket}
        </Text>

        <Text style={styles.sectionTitle}>Net Stroke Leaks (Strokes Gained)</Text>
        <View>
          {worstFirst.map((category) => (
            <View key={category} style={styles.row}>
              <Text style={styles.leakLabel}>{CATEGORY_LABELS[category]}</Text>
              <Text style={styles.leakValue}>
                {formatSigned(analytics.strokes_gained.by_category[category])}
              </Text>
            </View>
          ))}
          <View style={[styles.row, { marginTop: 4, borderTopWidth: 1, borderTopColor: "#ded2b4", paddingTop: 4 }]}>
            <Text style={[styles.leakLabel, { fontWeight: 700 }]}>Total</Text>
            <Text style={[styles.leakValue, { fontWeight: 700 }]}>
              {formatSigned(analytics.strokes_gained.total)}
            </Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Strike Patterns (Approach Shots)</Text>
        <View>
          {strikePatterns.length === 0 ? (
            <Text style={styles.bulletBody}>No approach shots recorded for this round.</Text>
          ) : (
            strikePatterns.map((pattern) => (
              <View key={pattern.label} style={styles.row}>
                <Text style={styles.leakLabel}>{pattern.label}</Text>
                <Text style={styles.leakValue}>{pattern.count}</Text>
              </View>
            ))
          )}
        </View>

        <Text style={styles.sectionTitle}>Tiger 5 Metrics</Text>
        <View style={styles.statGrid}>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>Clean Card Index</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.clean_card_index}%</Text>
          </View>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>Doubles+</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.double_bogeys_or_worse}</Text>
          </View>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>3-Putts</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.three_putts}</Text>
          </View>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>Par 5 Bogeys</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.par_five_bogeys}</Text>
          </View>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>Blown Recoveries (&lt;50y)</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.blown_recoveries_inside_50}</Text>
          </View>
          <View style={styles.statTile}>
            <Text style={styles.statLabel}>Penalties (&lt;150y)</Text>
            <Text style={styles.statValue}>{analytics.tiger_five.penalties_inside_150}</Text>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Recommended Coaching Agenda</Text>
        <View>
          {combines.length === 0 ? (
            <Text style={styles.bulletBody}>
              No weaknesses flagged from this player&apos;s data on file yet.
            </Text>
          ) : (
            combines.map((combine) => (
              <View key={combine.weakness} style={styles.bullet} wrap={false}>
                <Text style={styles.bulletTitle}>{combine.name}</Text>
                <Text style={styles.bulletBody}>{pdfSafeText(combine.instructions)}</Text>
                <Text style={styles.bulletMeta}>Target: {pdfSafeText(combine.target_metric)}</Text>
              </View>
            ))
          )}
        </View>

        <Text style={styles.footer}>
          Generated by Debrief Golf on {new Date().toLocaleDateString()}.
        </Text>
      </Page>
    </Document>
  );
}
