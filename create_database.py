import sqlite3

# Connect to SQLite database (creates the file if it doesn’t exist)
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Create `patients` table
cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    codOspite INTEGER PRIMARY KEY,
    idRicovero INTEGER,
    nome TEXT,
    cognome TEXT,
    sesso TEXT,
    dataNascita TEXT,
    codiceFiscale TEXT,
    idProfilo INTEGER,
    descrProfilo TEXT,
    idSede INTEGER,
    idReparto INTEGER,
    dal TEXT,
    al TEXT,
    attivo BOOLEAN
);
""")

# Create the `falls` table with all fields
cursor.execute("""
CREATE TABLE IF NOT EXISTS falls (
    fall_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    deletedData TEXT,
    hashAnnulla TEXT,
    tipoBlocco TEXT,
    bozza TEXT,
    permessiAnnulla TEXT,
    hashConvalidatore TEXT,
    codEnte INTEGER,
    tipoScheda TEXT,
    compilatore INTEGER,
    deambulante TEXT,
    ausili INTEGER,
    ausiliAltro TEXT,
    apparecchioAcustico TEXT,
    occhiali TEXT,
    altraProtesi TEXT,
    presenzaTestimoni TEXT,
    luogoCaduta INTEGER,
    luogoCadutaAltro TEXT,
    codSede INTEGER,
    codReparto INTEGER,
    illuminazione TEXT,
    ostacoli TEXT,
    ostacoliTipo TEXT,
    tipoPavimento TEXT,
    fattoreAmbientaleAltro TEXT,
    fattoreAmbientaleAltroDescr TEXT,
    attivitaSvolta INTEGER,
    calzatura INTEGER,
    calzaturaAllacciata TEXT,
    calzaturaAltro TEXT,
    contenzione TEXT,
    patologiaAcuta TEXT,
    demenza TEXT,
    sedazione TEXT,
    cadutePrecedenti TEXT,
    cadutePrecedentiQuando TEXT,
    descrizioneCaduta TEXT,
    fratture TEXT,
    prontoSoccorso TEXT,
    conseguenzeCaduta TEXT,
    altraProtesiDescr TEXT,
    testimoniOperatori TEXT,
    apparecchioAcusticoInUso TEXT,
    occhialiInUso TEXT,
    altraProtesiInUso TEXT,
    attivitaSvoltaDescr TEXT,
    codStanza INTEGER,
    contenzioneTipo TEXT,
    farmaciAssunti TEXT,
    provvedimenti TEXT,
    conseguenze INTEGER,
    provv TEXT,
    progrEpilessia TEXT,
    tipologiaCaduta TEXT,
    modalitaCaduta TEXT,
    autoreSegn TEXT,
    idRicovero INTEGER,
    descAnte TEXT,
    tipoCaduta TEXT,
    evento TEXT,
    nominativo TEXT,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    testimoni TEXT,
    operatori TEXT,
    listaCompilatori TEXT,
    dataUltimaCaduta TEXT,
    history TEXT,
    operatore INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

# Dictionary for diary tables
diary_types = {
    13: "diario_medico",
    14: "diario_infermieristico",
    15: "diario_sociale",
    16: "diario_assistenziale",
    17: "diario_riabilitativo"
}

# Create separate tables for each diary type with `tipologia`
for diary_id, table_name in diary_types.items():
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER,
        idRicovero INTEGER,
        compilatoreNominativo TEXT,
        compilatoreFigProf TEXT,
        tipo TEXT,
        nomeForm TEXT,
        dataOra TEXT,
        testoDiario TEXT,
        coloreS2 TEXT,
        coloreLabel INTEGER,
        tipologia TEXT,  -- ✅ Added tipologia field
        FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
    );
    """)

cursor.execute("""
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    nomeForm TEXT,
    dataOra TEXT,
    pressioneMaxOrto REAL,
    pressioneMinOrto REAL,
    pressioneMaxClino REAL,
    pressioneMinClino REAL,
    pressioneMaxNoSpec REAL,
    pressioneMinNoSpec REAL,
    frequenza INTEGER,
    freqRespiratoria INTEGER,
    temperatura REAL,
    curvaGli TEXT,
    peso REAL,
    spo2 REAL,
    spo2ot REAL,
    spo2NoSpec REAL,
    oSpo2ot REAL,
    diuresi TEXT,
    alvo TEXT,
    sonno TEXT,
    mobilita TEXT,
    comportamento TEXT,
    comportamentoAttivita TEXT,
    avpu TEXT,
    altezza REAL,
    tipoRespirazione TEXT,
    tipoFreqCardiaca TEXT,
    dolore TEXT,
    bmi REAL,
    inr REAL,
    ciclo TEXT,
    warningPressioneMaxOrto BOOLEAN,
    warningPressioneMinOrto BOOLEAN,
    warningPressioneMaxClino BOOLEAN,
    warningPressioneMinClino BOOLEAN,
    warningFrequenza BOOLEAN,
    warningFreqRespiratoria BOOLEAN,
    warningTemperatura BOOLEAN,
    warningCurvaGli BOOLEAN,
    warningPeso BOOLEAN,
    warningSpo2 BOOLEAN,
    warningSpo2ot BOOLEAN,
    warningDiuresi BOOLEAN,
    warningAlvo BOOLEAN,
    warningSonno BOOLEAN,
    warningMobilita BOOLEAN,
    warningComportamento BOOLEAN,
    warningTipoRespirazione BOOLEAN,
    warningTipoFreqCardiaca BOOLEAN,
    warningBmi BOOLEAN,
    warningInr BOOLEAN,
    testAlcool TEXT,
    testDroga TEXT,
    testGravidanza TEXT,
    descrizioneDroga TEXT,
    turno TEXT,
    tipologia TEXT,
    listIndex INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")


# Create `medications` table for current medications
cursor.execute("""
CREATE TABLE IF NOT EXISTS medications (
    med_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    codArticolo INTEGER,
    aic TEXT,
    dataInizio TEXT,
    dataFine TEXT,
    qtaStandard REAL,
    tipoTerapia TEXT,
    desFarmaco TEXT,
    desViaDiSomm TEXT,
    desUniMis TEXT,
    principioAttivo TEXT,
    orari TEXT,
    dosi TEXT,
    storico BOOLEAN DEFAULT 0,  -- 0 for active, 1 for historical
    isChiusa BOOLEAN DEFAULT 0,  -- Indicates if the therapy was closed
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS intake (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    data TEXT,
    tipo TEXT,
    quantita REAL,
    tipoRecord TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    giornoDellaSettimana INTEGER,
    nomeIcona TEXT,
    oraConvalida TEXT,
    convalidato BOOLEAN,
    note TEXT,
    bozza BOOLEAN,
    regAnnullate BOOLEAN,
    tipoBlocco TEXT,
    permessiAnnulla TEXT,
    codEnte INTEGER,
    hashAnnulla TEXT,
    deletedData TEXT,
    nominativo TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS personal_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codOspite INTEGER UNIQUE,
    nome TEXT,
    cognome TEXT,
    sesso TEXT,
    dataNascita TEXT,
    codiceFiscale TEXT UNIQUE,
    cittadinanza TEXT,
    comuneNascita TEXT,
    desComuneNascita TEXT,
    desProvinciaNascita TEXT,
    desNazioneNascita TEXT,
    statoCivile TEXT,
    gradoIstruzione TEXT,
    professione TEXT,
    telefono1 TEXT,
    telefono2 TEXT,
    email TEXT,

    -- Additional Fields
    codiceRegionale TEXT,
    codiceSanitario TEXT,
    lingua TEXT,
    testamento TEXT,
    codiceAccoglienza TEXT, 
    codiceProfilo TEXT,    

    -- Address & Residence
    indirizzo TEXT,
    cap TEXT,
    comune_residenza TEXT,
    provincia_residenza TEXT,

    -- Hospitalization
    ricovero_id INTEGER,
    ricovero_dal TEXT,
    ricovero_al TEXT,
    tipo_ricovero TEXT,
    reparto TEXT,
    sede TEXT,
    idSede INTEGER,
    idReparto INTEGER,

    -- Regional Parameters
    idTipoProvenienza INTEGER,
    motivoIngresso TEXT,
    iniziativaRichiesta INTEGER,
    tipoRicovero INTEGER,
    sosiaProfessione INTEGER,
    sosiaSituazionePens INTEGER,
    
    FOREIGN KEY (codOspite) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codOspite INTEGER,
    nomePersona TEXT,
    telefono1 TEXT,
    telefono2 TEXT,
    telefono3 TEXT,
    fax TEXT,
    email TEXT,
    note TEXT,
    delegaDenaro TEXT,
    garante TEXT,
    rating INTEGER,
    gradoParentela INTEGER,
    desGradoParentela TEXT,
    dataNascita TEXT,
    comuneNascita TEXT,
    nazioneNascita TEXT,
    codiceFiscale TEXT,
    indirizzo TEXT,
    cap TEXT,
    comune TEXT,
    provincia TEXT,
    desComune TEXT,
    desNazione TEXT,
    FOREIGN KEY (codOspite) REFERENCES personal_data(codOspite)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hospital_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idRicovero INTEGER,
    dataDal TEXT,
    dataAl TEXT,
    idSede INTEGER,
    idReparto INTEGER,
    idStanza INTEGER,
    idLetto INTEGER,
    desSede TEXT,
    desReparto TEXT,
    tipoMov TEXT,
    desStato TEXT,
    desStanza TEXT,
    numeroStanza TEXT,
    stanzaAdibita TEXT,
    numeroLetti TEXT,
    desLetto TEXT,
    numeroLetto TEXT,
    idResidenza INTEGER,
    FOREIGN KEY (idRicovero) REFERENCES personal_data(ricovero_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hospitalizations_history (
    id INTEGER PRIMARY KEY,
    codOspite INTEGER,
    idProfilo INTEGER,
    dal TEXT,
    al TEXT,
    idRicoveroCU INTEGER UNIQUE,
    chiusoDa INTEGER,
    chiusoData TEXT,
    statoArchiviazione TEXT,
    archiviazioneInit TEXT,
    nosologico TEXT,
    codicePsiche TEXT,
    autoSomministrazione TEXT,
    fineRiconciliazione TEXT,
    compilatoreChiusura TEXT,
    idSwEsterni TEXT,
    coRicoveroLight TEXT,
    nosologicoFormatted TEXT,
    checkNosologico TEXT,
    motivoDimissioneCu2 TEXT,
    idRicoveroCollegato INTEGER,
    idOrgProfilo INTEGER,
    descrProfilo TEXT
);
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS patient_absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idRicovero INTEGER,
    dal TEXT,
    al TEXT,
    motivoUscita INTEGER,
    idAssenzaCo INTEGER,
    codiceOspedale TEXT,
    desMotivo TEXT,
    desOspedale TEXT,
    idAssenzaCollegata INTEGER,
    FOREIGN KEY (idRicovero) REFERENCES personal_data(ricovero_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS contenzioni (
    contenzione_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    dataInizio TEXT,
    dataFine TEXT,
    dataRevisioneFormatted TEXT,
    motivazione TEXT,
    mezziContenzione TEXT,
    mezziContenzioneDecodificati TEXT,
    monitoraggio TEXT,
    alternative TEXT,
    ospiteAffettoDa TEXT,
    famigliaInformata TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    tipoBlocco TEXT,
    contenzioneQuando TEXT,
    note TEXT,
    scadenza INTEGER,
    agendaFunzione TEXT,
    fineMese TEXT,
    permanente TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS dispositivi_contenzione (
    id INTEGER PRIMARY KEY,
    codArea INTEGER,
    codDomanda INTEGER,
    descrizione TEXT,
    descrizione_de TEXT,
    ordinamento INTEGER,
    coefficiente REAL,
    codifica TEXT,
    abilitata TEXT,
    coloreCodificaS2 TEXT,
    etichetta TEXT,
    label TEXT,
    inputValueStr TEXT,
    inputValueInt INTEGER
);
""")

# Insert default values into dispositivi_contenzione
dispositivi_values = [
    (3192, 5, 50, "Cintura addominale", None, None, None, None, None, None, None, "Cintura addominale", None, 3192),
    (7918, 5, 50, "Cintura pelvica", None, None, None, None, "T", None, None, "Cintura pelvica", None, 7918),
    (7922, 5, 50, "Divaricatore inguinale", None, None, None, None, "T", None, None, "Divaricatore inguinale", None, 7922),
    (3191, 5, 50, "Fascia a corpo a letto", None, None, None, None, "F", None, None, "Fascia a corpo a letto", None, 3191),
    (7924, 5, 50, "Lenzuolo anticaduta", None, None, None, None, "T", None, None, "Lenzuolo anticaduta", None, 7924),
    (7919, 5, 50, "Polsiere", None, None, None, None, "T", None, None, "Polsiere", None, 7919),
    (3193, 5, 50, "Spondine letto", None, None, None, None, None, None, None, "Spondine letto", None, 3193),
    (3194, 5, 50, "Tavolino", None, None, None, None, None, None, None, "Tavolino", None, 3194),
    (7920, 5, 50, "Tutone", None, None, None, None, "T", None, None, "Tutone", None, 7920)
]

cursor.executemany("""
INSERT OR IGNORE INTO dispositivi_contenzione (
    id, codArea, codDomanda, descrizione, descrizione_de, ordinamento,
    coefficiente, codifica, abilitata, coloreCodificaS2, etichetta,
    label, inputValueStr, inputValueInt
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", dispositivi_values)



cursor.execute("""
CREATE TABLE IF NOT EXISTS lesioni (
    lesione_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    dataFine TEXT,
    sedeLesione INTEGER,
    sedeLesioneDecod TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    dataRecenteDett TEXT,
    dataFineFormatted TEXT,
    dataFormatted TEXT,
    idUltimoDett INTEGER,
    idUltimaMedicazioneV1 INTEGER,
    presInIngr TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS lesioni_dettagli (
    dettaglio_id INTEGER PRIMARY KEY,
    lesione_id INTEGER,
    data TEXT,
    lunghezza REAL,
    larghezza REAL,
    profondita REAL,
    superficie REAL,
    lunghezza_s2 REAL,
    larghezza_s2 REAL,
    profondita_s2 REAL,
    stadio INTEGER,
    tipoTessuto TEXT,
    essudato INTEGER,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    stadioFormatted TEXT,
    numeroLesioni TEXT,
    FOREIGN KEY (lesione_id) REFERENCES lesioni(lesione_id)
);
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS lesioni_medicazioni (
    id INTEGER PRIMARY KEY,
    idLesione INTEGER,
    idRicovero INTEGER,
    idMedTe INTEGER,
    idCassetto INTEGER,
    codArticolo TEXT,
    aic TEXT,
    ordine TEXT,
    descrCassetto TEXT,
    descrFarmacoFormatted TEXT,
    data TEXT,
    compilatore INTEGER,
    FOREIGN KEY (idLesione) REFERENCES lesioni(lesione_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS lesione_med_dettagli (
    id INTEGER PRIMARY KEY,
    idLesione INTEGER,
    idMedTe INTEGER,
    idCassetto INTEGER,
    codArticolo TEXT,
    aic TEXT,
    ordine TEXT,
    descrCassetto TEXT,
    descrFarmacoFormatted TEXT,
    data TEXT,
    compilatore INTEGER,
    idRicovero INTEGER,
    FOREIGN KEY (idLesione) REFERENCES lesioni(lesione_id)
);
""")


# Create `pi` table (Piano Individualizzato)
cursor.execute("""
CREATE TABLE IF NOT EXISTS pi (
    pi_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    deletedData TEXT,
    tipoBlocco TEXT,
    bozza BOOLEAN,
    permessiAnnulla TEXT,
    codEnte INTEGER,
    idRicovero INTEGER,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    schedavalida BOOLEAN,
    nominativo TEXT,
    isCopia BOOLEAN,
    listaCompilatori TEXT,
    team TEXT,
    listaAree TEXT,
    areaDescriptions TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

# Create `pai` table (Piano Assistenziale Individualizzato)
cursor.execute("""
CREATE TABLE IF NOT EXISTS pai (
    pai_id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idTe INTEGER,
    data TEXT,
    codArea INTEGER,
    nomeArea TEXT,
    patologia INTEGER,
    descrizionePatologia TEXT,
    problemi TEXT,
    obiettivi TEXT,
    strategie TEXT,
    rispObiettiviDesc TEXT,
    indicatori TEXT,
    note TEXT,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    listaCompilatori TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

# Create `painad` table
cursor.execute("""
CREATE TABLE IF NOT EXISTS painad (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    punteggio INTEGER,
    punteggioMassimo INTEGER,
    domande TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

# Create `nrs` table (Scala Numerica del Dolore)
cursor.execute("""
CREATE TABLE IF NOT EXISTS nrs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    valore INTEGER,
    note TEXT,
    scadenza INTEGER,
    tipo INTEGER,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS cirs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    scadenza INTEGER,
    convertito TEXT,
    punteggio INTEGER,
    cardiaca INTEGER,
    ipertensione INTEGER,
    vascolari INTEGER,
    respiratorie INTEGER,
    oongl INTEGER,
    appGiSup INTEGER,
    appGiInf INTEGER,
    epatiche INTEGER,
    renali INTEGER,
    patGenUri INTEGER,
    sisMusSche INTEGER,
    sisNervoso INTEGER,
    endoMeta INTEGER,
    psichiatrico INTEGER,
    indiceComorbilita INTEGER,
    indiceSeverita REAL,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS must (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    step1 INTEGER,
    step2 INTEGER,
    step3 INTEGER,
    punteggio INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mna (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    scadenza INTEGER,
    convertito TEXT,
    bmi REAL,
    mac REAL,
    cc REAL,
    perditaPeso INTEGER,
    viveIndipendentemente INTEGER,
    piuDi3Farmaci INTEGER,
    stressPsicologici INTEGER,
    mobilita INTEGER,
    problemiNeuro INTEGER,
    piagheDecubito INTEGER,
    pastiCompleti INTEGER,
    consuma INTEGER,
    consumaFruttaVerdura INTEGER,
    riduzioneAppetito INTEGER,
    liquidiAssunti INTEGER,
    comeMangia INTEGER,
    ritieneDiAvereProb INTEGER,
    statoSalute INTEGER,
    consuma1 TEXT,
    consuma2 TEXT,
    consuma3 TEXT,
    peso REAL,
    altezza REAL,
    bmiCalcolata REAL,
    dataBmi TEXT,
    note TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS esame_neurologico (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    statoCoscienza INTEGER,
    comportamento TEXT,
    coscienzaMalattia INTEGER,
    linguaggio INTEGER,
    statoEmotivo TEXT,
    disturbi TEXT,
    stazioneEretta TEXT,
    tonoDX INTEGER,
    tonoSX INTEGER,
    nominativo TEXT,
    note TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS esame_obiettivo (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    codEnte INTEGER,
    codOspite INTEGER,
    tipoScheda INTEGER,
    condGen TEXT,
    statoNutizioneKg REAL,
    statoNutrizioneBmi REAL,
    statoNutrizioneAltezza REAL,
    statoSang TEXT,
    statoIdr TEXT,
    modificazionePeso TEXT,
    cute TEXT,
    occhi TEXT,
    vista TEXT,
    udito TEXT,
    denti TEXT,
    dentiAltro TEXT,
    lingua TEXT,
    collo TEXT,
    tiroide TEXT,
    pressioneArtOrto TEXT,
    pressioneArtClino TEXT,
    soffiCarotidei TEXT,
    soffiAortici TEXT,
    soffiFemorali TEXT,
    polsi TEXT,
    polsiIposfigmia TEXT,
    polsiAssenti TEXT,
    torace TEXT,
    addome TEXT,
    fegato TEXT,
    milza TEXT,
    sistemaLinfoGhiand TEXT,
    apparatoOssa TEXT,
    apparatoOssaDolore TEXT,
    apparatoOssaLimitazioneFunz TEXT,
    artiNormali TEXT,
    artiEdemi TEXT,
    artiVarici TEXT,
    artiFlebopatie TEXT,
    artiCompstasi TEXT,
    artiAmputazione TEXT,
    artiProtesi TEXT,
    piedi TEXT,
    piediDeform TEXT,
    apparatoUrogenit TEXT,
    repertoProst TEXT,
    esplorazioneRettale TEXT,
    decubiti TEXT,
    cuore TEXT,
    pressioneArtCuore TEXT,
    mammelle TEXT,
    masseMuscolari TEXT,
    sensorio TEXT,
    cmAspetto TEXT,
    cmAnnessi TEXT,
    cmManifestazioni TEXT,
    note TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS schede_biografiche (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    codArea INTEGER,
    descrizione TEXT,
    note TEXT,
    coefficiente INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    ordinamento INTEGER,
    tipoBlocco TEXT,
    permessiAnnulla TEXT,
    bozza BOOLEAN,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS cartella (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    peso REAL,
    statoCoscienza INTEGER,
    respiro TEXT,
    abitudiniAlcool TEXT,
    abitudiniFumo TEXT,
    diuresiRegolare TEXT,
    ausiliPannolone TEXT,
    ausiliUrocontrol TEXT,
    ausiliCatetere TEXT,
    mobilizzazione TEXT,
    protesi TEXT,
    ausilio1 TEXT,
    ausilio2 TEXT,
    tipoAusili INTEGER,
    igienePersonale TEXT,
    visoManiBocca TEXT,
    intima TEXT,
    bagnoDoccia TEXT,
    vestirsi TEXT,
    farmaciSonno TEXT,
    dolore TEXT,
    decubito TEXT,
    ausiliMaterasso TEXT,
    ausiliCuscini TEXT,
    udito TEXT,
    linguaggio TEXT,
    orientamento TEXT,
    comportamento TEXT,
    note TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pairaccoltadati (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    pressioneMax INTEGER,
    pressioneMin INTEGER,
    frequenzaCardiaca INTEGER,
    temperatura REAL,
    edemi TEXT,
    respiro TEXT,
    peso REAL,
    altezza REAL,
    presenzaDoloreMovimento TEXT,
    utilizzaProtesiPresidi TEXT,
    problemiMinzione TEXT,
    problemiAlvo TEXT,
    personaCollabora TEXT,
    siEsprimeChiaramente TEXT,
    occhiali TEXT,
    problemiUdito TEXT,
    conosceSistemiSicurezza TEXT,
    microclimaAutonomo TEXT,
    rischioCadute TEXT,
    rischioInfezione TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS fisioterapia (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    idRicovero INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    listaModelli TEXT,  -- serialized JSON: lstModelli with diagnosi, patologie, postura, ecc.
    agendaFunzione TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS barthel (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    punteggio INTEGER,
    punteggioMassimo INTEGER,
    igiene_personale INTEGER,
    bagno_doccia INTEGER,
    alimentazione INTEGER,
    abbigliamento INTEGER,
    cont_inte INTEGER,
    cont_uri INTEGER,
    trasferimento INTEGER,
    toilette INTEGER,
    scale INTEGER,
    deambulazione INTEGER,
    carrozzina INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS braden (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    punteggio INTEGER,
    punteggioMassimo INTEGER,
    scadenza INTEGER,
    percezione_sensoriale INTEGER,
    umidita INTEGER,
    attivita INTEGER,
    mobilita INTEGER,
    nutrizione INTEGER,
    frizione_scivolamento INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tinetti (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    scadenza INTEGER,
    punteggio INTEGER,
    punteggio_andatura INTEGER,
    punteggio_equilibrio INTEGER,
    andInizioDeamb INTEGER,
    andLunghPassoDx INTEGER,
    andAltezzaPassoDx INTEGER,
    andLunghPassoSx INTEGER,
    andAltezzaPassoSx INTEGER,
    andSimmetria INTEGER,
    andContinuitaPasso INTEGER,
    andTraiettoria INTEGER,
    andTronco INTEGER,
    andCammino INTEGER,
    eqDaSeduto INTEGER,
    eqAlzarsiSedia INTEGER,
    eqTentativo INTEGER,
    eqStazEretta5Sec INTEGER,
    eqStazErettaProl INTEGER,
    eqRomberg INTEGER,
    eqRombergSens INTEGER,
    eqGirarsi INTEGER,
    eqGirarsiStab INTEGER,
    eqSedersi INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conley (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    scadenza INTEGER,
    punteggio INTEGER,
    domanda1 INTEGER,
    domanda2 INTEGER,
    domanda3 INTEGER,
    domanda4 INTEGER,
    domanda5 INTEGER,
    domanda6 INTEGER,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS morse (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    scadenza INTEGER,
    cadute INTEGER,
    diagnosi INTEGER,
    mobilita INTEGER,
    terapia INTEGER,
    andatura INTEGER,
    statoMentale INTEGER,
    totale INTEGER,
    note TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS attivita (
    id INTEGER PRIMARY KEY,
    idPianificazione INTEGER,
    idAttivita INTEGER,
    title TEXT,
    description TEXT,
    data TEXT,
    dalle TEXT,
    alle TEXT,
    color TEXT,
    compilatore INTEGER,
    idRicovero INTEGER,
    codImg INTEGER,
    allDay BOOLEAN,
    calendarId INTEGER,
    startDate TEXT,
    endDate TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mmse (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    punteggio INTEGER,
    scadenza INTEGER,
    fattoreCorrezione REAL,
    convertito TEXT,
    nonSomministrabile TEXT,
    orientamento INTEGER,
    spazio INTEGER,
    memoria INTEGER,
    memoriaTent INTEGER,
    attenzione INTEGER,
    richiamo INTEGER,
    linguaggio INTEGER,
    ripetizione INTEGER,
    compito INTEGER,
    ordine INTEGER,
    frase INTEGER,
    copiaDisegno INTEGER,
    totale INTEGER,
    corretto REAL,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gbs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    note TEXT,
    scadenza INTEGER,
    convertito TEXT,
    nonsomministrabile TEXT,
    sdconfusione INTEGER,
    sdirritabilita INTEGER,
    sdansia INTEGER,
    sdangoscia INTEGER,
    sddepressione INTEGER,
    sdirrequietezza INTEGER,
    agendaFunzione TEXT,
    FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS manual_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ricovero_id INTEGER,
    check_key TEXT,
    override_status TEXT,
    note TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ricovero_id, check_key),
    FOREIGN KEY (ricovero_id) REFERENCES hospitalizations_history(id)
);
""")


# Save and close
conn.commit()
conn.close()

print("✅ Database schema updated with all required fields!")
