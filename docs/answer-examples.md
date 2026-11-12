# Answer examples (section 3)

Real runs against `claude-haiku-5-5` (`regulatory-helper ask` / `chat`), mode `hybrid`, k = 6, rewriting on, threshold 0.60.
Erzeugt am 2026-11-12. Fragen, Suchanfragen und Antworten sind unverändert ausgegeben; Zitate sind auf 350 Zeichen gekürzt.

## Schwelle (vorläufig)
Kosinus des besten Treffers (Vektormodell `bge-small-en-v1.5`), gemessen mit englischen Suchanfragen:

| Anfrage | bester Kosinus |
|---|---|
| best pizza restaurant | 0.44 |
| recipe for chocolate cake | 0.48 |
| weather forecast for tomorrow in Berlin | 0.49 |
| mortgage interest rates | 0.60 |
| how to train a neural network for football | 0.64 |
| software classification rule medical device | 0.82 |
| right to erasure personal data | 0.88 |

Vorläufiger Wert **0.60** (`Config.threshold`): Unsinn ohne Regulatorik-Bezug wird ohne zweiten Haiku-Aufruf abgewiesen, echte Fragen liegen weit darüber (0.80 bis 0.86). Grenzfälle mit KI- oder Datenbezug (0.6 bis 0.65) laufen durch und Haiku entscheidet (`found: false`). Die endgültige Schwelle gehört in die Validierung (Abschnitt 5).

## Beobachtungen
- Das Query Rewriting liefert eine englische Fachsprache-Anfrage, auch aus deutschen Fragen und Folgefragen („Und welche Klasse hätte sie dann?" wird zu einer Anfrage mit Rule 11 und Kontext).
- Haiku benennt meist selbst, was die Passagen nicht klären. Gewollt (kein Raten), aber die Antworten sind dadurch teils lang und vorsichtig.
- Kosten: ca. 0,03 bis 0,09 Cent pro Frage (Haiku 5.5, $0.10/$0.50 je 1M Tokens), 2 Aufrufe. Die Ausgabetokens sind höher als die Antwort (ca. 750 bis 1000), weil Haiku 5.5 intern nachdenkt (Effort `low`).

## Einzelfragen

### 1. 
**Frage (de):** Muss meine Software, die Laborwerte nur anzeigt, nach MDR als Medizinprodukt eingestuft werden?

- Umformulierte Suchanfrage: `medical device software qualification displaying laboratory results only, classification under MDR Article 2(1) and Annex VIII Rule 11`
- Bester Treffer (Kosinus): 0.798, Ergebnis: `answered`
- Tokens ein/aus: 1586/788, Aufrufe: 2, Kosten: $0.00055

**Antwort:** Die Quellen beantworten diese Frage nur teilweise. Nach Erwägungsgrund 19 ist Software als Medizinprodukt zu qualifizieren, wenn der Hersteller sie ausdrücklich für einen medizinischen Zweck bestimmt, während Software für allgemeine Zwecke, auch im Gesundheitswesen, keines ist. Ob eine reine Laborwert-Anzeige einen solchen medizinischen Zweck hat, geht aus den Quellen nicht hervor. Wird die Software dagegen für diagnostische oder therapeutische Entscheidungen bereitgestellt, greift die Regel in Anhang VIII Nr. 6.3 (Regel 11), nach der solche Informationssoftware in Klasse IIa, IIb oder III fällt, je nach möglicher Auswirkung der Entscheidung. Die Zweckbestimmung des Herstellers ist also entscheidend; die Quellen enthalten dazu keine weitere Festlegung.

> **[MDR-REC-19]** MDR Recital 19 [recital of the original 2017 text]: "It is necessary to clarify that software in its own right, when specifically intended by the manufacturer to be used for one or more of the medical purposes set out in the definition of a medical device, qualifies as a medical device, while software for general purposes, even when used in a healthcare setting, or software intended for life-style an…"
> **[MDR-ANNEX-VIII-6.3]** MDR Annex VIII, point 6.3 (Rule 11): "Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have an impact that may cause: — death or an irreversible deterioration of a person's state of health, in which case it is in class III; or — a serious deterioration of a person's state…"

### 2. 
**Frage (de):** Welche Pflichten habe ich, wenn mein Produkt ein KI-Modell zur Diagnoseunterstützung enthält?

- Umformulierte Suchanfrage: `obligations provider medical device containing AI model diagnostic support high-risk AI system AI Act Article 6 MDR Article 10 conformity assessment`
- Bester Treffer (Kosinus): 0.825, Ergebnis: `answered`
- Tokens ein/aus: 2768/1110, Aufrufe: 2, Kosten: $0.00083

**Antwort:** Die Passagen beantworten dies nur teilweise. Ob Ihr Diagnoseunterstützungs-KI als Hochrisiko-System gilt, lässt sich aus ihnen nicht ableiten, und Medizinprodukte nach der MDR werden darin nicht behandelt. Wenn Sie Anbieter eines Hochrisiko-KI-Systems sind, gelten die Pflichten aus Art. 16 AI Act, u. a. Konformität mit Abschnitt 2 sicherstellen, Qualitätsmanagementsystem (Art. 17), Dokumentation (Art. 18), Konformitätsbewertung vor dem Inverkehrbringen (Art. 43), EU-Konformitätserklärung (Art. 47), CE-Kennzeichnung (Art. 48) und Registrierung (Art. 49(1)). Die Wahl des Konformitätsbewertungsverfahrens (interne Kontrolle nach Anhang VI oder Anhang VII mit benannter Stelle) hängt nach Art. 43(1) davon ab, ob harmonisierte Normen angewandt wurden. Sind Sie Importeur oder Händler, gelten die Prüf- und Korrekturpflichten nach Art. 23 bzw. Art. 24(4), und Sie können nach Art. 25(1) wie ein Anbieter behandelt werden, etwa wenn Sie Ihren Namen auf ein bereits eingeführtes System setzen. Ob die Einstufung als hochriskant überhaupt zutrifft, ist nicht geklärt; bei einer Selbsteinschätzung als nicht hochriskant wären Dokumentation und Registrierung nach Art. 6(4) zu beachten.

> **[AIACT-16]** AI Act Art. 16: "Providers of high-risk AI systems shall: (a) ensure that their high-risk AI systems are compliant with the requirements set out in Section 2; (b) indicate on the high-risk AI system or, where that is not possible, on its packaging or its accompanying documentation, as applicable, their name, registered trade name or registered trade mark, the addre…"
> **[AIACT-43-1]** AI Act Art. 43(1): "For high-risk AI systems listed in point 1 of Annex III, where, in demonstrating the compliance of a high-risk AI system with the requirements set out in Section 2, the provider has applied harmonised standards referred to in Article 40, or, where applicable, common specifications referred to in Article 41, the provider shall opt for one of the fol…"
> **[AIACT-23-1]** AI Act Art. 23(1): "Before placing a high-risk AI system on the market, importers shall ensure that the system is in conformity with this Regulation by verifying that: (a) the relevant conformity assessment procedure referred to in Article 43 has been carried out by the provider of the high-risk AI system; (b) the provider has drawn up the technical documentation in a…"
> **[AIACT-24-4]** AI Act Art. 24(4): "A distributor that considers or has reason to consider, on the basis of the information in its possession, a high-risk AI system which it has made available on the market not to be in conformity with the requirements set out in Section 2, shall take the corrective actions necessary to bring that system into conformity with those requirements, to wi…"
> **[AIACT-25-1]** AI Act Art. 25(1): "Any distributor, importer, deployer or other third-party shall be considered to be a provider of a high-risk AI system for the purposes of this Regulation and shall be subject to the obligations of the provider under Article 16, in any of the following circumstances: (a) they put their name or trademark on a high-risk AI system already placed on th…"
> **[AIACT-6-4]** AI Act Art. 6(4): "A provider who considers that an AI system referred to in Annex III is not high-risk shall document its assessment before that system is placed on the market or put into service. Such provider shall be subject to the registration obligation set out in Article 49(2). Upon request of national competent authorities, the provider shall provide the docu…"

### 3. 
**Frage (en):** Under which conditions may health data be processed for training a model?

- Umformulierte Suchanfrage: `conditions for processing health data special categories of personal data GDPR Article 9 scientific research purposes training artificial intelligence model Article 89`
- Bester Treffer (Kosinus): 0.857, Ergebnis: `answered`
- Tokens ein/aus: 2339/715, Aufrufe: 2, Kosten: $0.00059

**Antwort:** The passages do not address model training directly. Under Art. 9(1), processing health data is prohibited unless an Art. 9(2) exception applies. The relevant exceptions are Art. 9(2)(g) (substantial public interest), (h) (health care and management of health systems), (i) (public health), and (j) (archiving, scientific or historical research, or statistics under Art. 89(1)). Each requires a basis in Union or Member State law with suitable and specific safeguards. Recital 159 says scientific research should be interpreted broadly and may include privately funded research, but the passages do not state whether training a model qualifies as scientific research. Art. 9(4) allows Member States to add further conditions or limitations on health data processing. Where research processing applies, Art. 21(6) gives the data subject a right to object on grounds relating to their particular situation, unless the processing is necessary for a task carried out in the public interest. The passages do not settle whether any of these exceptions covers training a model, or which specific safeguards would apply.

> **[GDPR-9-1]** GDPR Art. 9(1): "Processing of personal data revealing racial or ethnic origin, political opinions, religious or philosophical beliefs, or trade union membership, and the processing of genetic data, biometric data for the purpose of uniquely identifying a natural person, data concerning health or data concerning a natural person's sex life or sexual orientation sha…"
> **[GDPR-9-2-s2]** GDPR Art. 9(2) (part 2/2): "Paragraph 1 shall not apply if one of the following applies: (g) processing is necessary for reasons of substantial public interest, on the basis of Union or Member State law which shall be proportionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamenta…"
> **[GDPR-9-4]** GDPR Art. 9(4): "Member States may maintain or introduce further conditions, including limitations, with regard to the processing of genetic data, biometric data or data concerning health."
> **[GDPR-REC-159]** GDPR Recital 159: "Where personal data are processed for scientific research purposes, this Regulation should also apply to that processing. For the purposes of this Regulation, the processing of personal data for scientific research purposes should be interpreted in a broad manner including for example technological development and demonstration, fundamental researc…"
> **[GDPR-21-6]** GDPR Art. 21(6): "Where personal data are processed for scientific or historical research purposes or statistical purposes pursuant to Article 89(1), the data subject, on grounds relating to his or her particular situation, shall have the right to object to processing of personal data concerning him or her, unless the processing is necessary for the performance of a…"
> **[GDPR-REC-53]** GDPR Recital 53: "Special categories of personal data which merit higher protection should be processed for health-related purposes only where necessary to achieve those purposes for the benefit of natural persons and society as a whole, in particular in the context of the management of health or social care services and systems, including processing by the manageme…"

### 4. 
**Frage (en):** What does Rule 11 say about software classification?

- Umformulierte Suchanfrage: `Annex VIII Rule 11 medical device software classification`
- Bester Treffer (Kosinus): 0.816, Ergebnis: `answered`
- Tokens ein/aus: 1444/235, Aufrufe: 2, Kosten: $0.00026

**Antwort:** Rule 11 (MDR Annex VIII, point 6.3) classifies software intended to provide information used to take diagnosis or therapy decisions as class IIa. It is class III if those decisions may cause death or irreversible deterioration of a person's state of health, and class IIb if they may cause a serious deterioration of health or a surgical intervention. Software intended to monitor physiological processes is class IIa, or class IIb if it monitors vital physiological parameters whose variations could cause immediate danger to the patient. All other software is class I.

> **[MDR-ANNEX-VIII-6.3]** MDR Annex VIII, point 6.3 (Rule 11): "Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have an impact that may cause: — death or an irreversible deterioration of a person's state of health, in which case it is in class III; or — a serious deterioration of a person's state…"

### 5. 
**Frage (de):** Wie wird das Wetter morgen in Aachen?

- Umformulierte Suchanfrage: `weather forecast tomorrow Aachen`
- Bester Treffer (Kosinus): 0.532, Ergebnis: `below_threshold`
- Tokens ein/aus: 298/16, Aufrufe: 1, Kosten: $0.00004

**Antwort:** Dazu finde ich nichts in den Quellen.


## Folgefragen-Sitzung (3 Runden)

### Runde 1

**Frage (de):** Ist meine App ein Medizinprodukt, wenn sie Patientendaten nur anzeigt?

- Umformulierte Suchanfrage: `medical device qualification software displaying patient data without medical purpose MDR Article 2(1) definition`
- Bester Treffer (Kosinus): 0.824, Ergebnis: `answered`
- Tokens ein/aus: 2030/702, Aufrufe: 2, Kosten: $0.00055

**Antwort:** Die Passagen beantworten dies nur teilweise. Software ist nach Art. 2 Abs. 1 MDR dann ein Medizinprodukt, wenn der Hersteller sie gezielt für einen der dort genannten medizinischen Zwecke bestimmt, etwa Diagnose, Überwachung, Vorhersage, Prognose oder Behandlung. Nach Erwägungsgrund 19 ist Software für allgemeine Zwecke auch dann kein Medizinprodukt, wenn sie im Gesundheitsbereich eingesetzt wird. Ob eine reine Anzeige von Patientendaten einen dieser Zwecke erfüllt, lassen die Passagen offen. Sie enthalten keine Aussage dazu, ob Anzeige allein als „Überwachung“ gilt. Entscheidend ist die vom Hersteller festgelegte Zweckbestimmung, die aus den Passagen allein nicht abschließend beurteilt werden kann.

> **[MDR-REC-19]** MDR Recital 19 [recital of the original 2017 text]: "It is necessary to clarify that software in its own right, when specifically intended by the manufacturer to be used for one or more of the medical purposes set out in the definition of a medical device, qualifies as a medical device, while software for general purposes, even when used in a healthcare setting, or software intended for life-style an…"
> **[MDR-2-1]** MDR Art. 2(1): "‘medical device’ means any instrument, apparatus, appliance, software, implant, reagent, material or other article intended by the manufacturer to be used, alone or in combination, for human beings for one or more of the following specific medical purposes:   — diagnosis, prevention, monitoring, prediction, prognosis, treatment or alleviation of di…"

### Runde 2

**Frage (de):** Und welche Klasse hätte sie dann?

- Umformulierte Suchanfrage: `medical device software classification rules Annex VIII Rule 11 Article 51 intended purpose monitoring display of patient data`
- Bester Treffer (Kosinus): 0.813, Ergebnis: `answered`
- Tokens ein/aus: 2244/827, Aufrufe: 2, Kosten: $0.00064

**Antwort:** Die Passagen legen keine feste Klasse fest, weil die Einstufung nach Anhang VIII Nr. 3.1 von der Zweckbestimmung abhängt. Nach Nr. 6.3 (Regel 11) wäre Software, die Informationen für diagnostische oder therapeutische Entscheidungen liefert, mindestens Klasse IIa, bei möglichen schweren Folgen Klasse IIb oder III. Software zur Überwachung physiologischer Prozesse wäre Klasse IIa, bei vitalen Parametern mit möglicher unmittelbarer Gefahr Klasse IIb. Sonstige Software fiele in Klasse I. Nach Nr. 3.3 wird eigenständige, von anderen Geräten unabhängige Software in ihrer eigenen Klasse eingestuft. Ob die reine Anzeige von Patientendaten unter eine dieser Regeln fällt, ist aus den Passagen nicht zu beantworten.

> **[MDR-ANNEX-VIII-6.3]** MDR Annex VIII, point 6.3 (Rule 11): "Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have an impact that may cause: — death or an irreversible deterioration of a person's state of health, in which case it is in class III; or — a serious deterioration of a person's state…"
> **[MDR-ANNEX-VIII-3.1]** MDR Annex VIII, point 3.1: "Application of the classification rules shall be governed by the intended purpose of the devices."
> **[MDR-ANNEX-VIII-3.3]** MDR Annex VIII, point 3.3: "Software, which drives a device or influences the use of a device, shall fall within the same class as the device. If the software is independent of any other device, it shall be classified in its own right."

### Runde 3

**Frage (de):** Welche Pflichten habe ich als Hersteller bei dieser Klasse?

- Umformulierte Suchanfrage: `manufacturer obligations medical device software classification Class I IIa IIb MDR Article 10 Annex VIII`
- Bester Treffer (Kosinus): 0.833, Ergebnis: `answered`
- Tokens ein/aus: 4103/882, Aufrufe: 2, Kosten: $0.00085

**Antwort:** Die Klasse ist aus den Passagen nicht festgelegt, weil sie von der Zweckbestimmung abhängt. Für Klasse IIa nennt Anhang XI Nr. 10 folgende Pflichten: Sie erklären per EU-Konformitätserklärung, dass die Produkte den technischen Unterlagen (Anhänge II und III) und den anwendbaren Anforderungen der MDR entsprechen (Nr. 10.1). Die benannte Stelle prüft die technischen Unterlagen stichprobenartig und stellt bei Bestätigung ein Zertifikat aus (Nr. 10.2 und 10.3). Weitere Stichproben werden im Rahmen der Überwachung geprüft (Nr. 10.4). Die Konformitätserklärung ist mindestens 10 Jahre nach dem Inverkehrbringen des letzten Geräts bereitzuhalten (Nr. 10.5). Pflichten für Klasse I oder IIb sowie für Klasse III werden in den Passagen nicht vollständig dargestellt. Anhang IX Nr. 5.1 betrifft nur implantierbare Produkte der Klasse III und aktive Produkte der Klasse IIb zur Verabreichung von Arzneimitteln, nicht die allgemeinen Herstellerpflichten.

> **[MDR-ANNEX-XI-10-s1]** MDR Annex XI, point 10 (part 1/2): "Application to class IIa devices 10.1. By way of derogation from Section 5, by virtue of the EU declaration of conformity the manufacturer shall be deemed to ensure and to declare that the class IIa devices in question are manufactured in conformity with the technical documentation referred to in Annexes II and III and meet the requirements of this…"
> **[MDR-ANNEX-VIII-6.3]** MDR Annex VIII, point 6.3 (Rule 11): "Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if such decisions have an impact that may cause: — death or an irreversible deterioration of a person's state of health, in which case it is in class III; or — a serious deterioration of a person's state…"
> **[MDR-ANNEX-IX-5.1-s1]** MDR Annex IX, point 5.1 (part 1/3): "(a) For class III implantable devices, and for class IIb active devices intended to administer and/or remove a medicinal product as referred to in Section 6.4. of Annex VIII (Rule 12), the notified body shall, having verified the quality of clinical data supporting the clinical evaluation report of the manufacturer referred to in Article 61(12), pr…"

Gesamtkosten dieser Läufe: $0.0043