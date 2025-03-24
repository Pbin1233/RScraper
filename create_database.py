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
    al TEXT
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
        FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
    );
    """)

cursor.execute("""
CREATE TABLE IF NOT EXISTS vitals_alternative (
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
    warningPressioneMaxOrto BOOLEAN,  -- ✅ Ensure these fields exist
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS intake (
    id INTEGER PRIMARY KEY,  -- this stores the record's own unique ID from the API
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
    
    -- 🆕 Additional detailed fields
    note TEXT,
    bozza BOOLEAN,
    regAnnullate BOOLEAN,
    tipoBlocco TEXT,  -- JSON string
    permessiAnnulla TEXT,  -- JSON string
    codEnte INTEGER,
    hashAnnulla TEXT,
    deletedData TEXT,
    nominativo TEXT,

    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
);
""")


# Create `vitals` table
cursor.execute("""
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    idRicovero INTEGER,
    data TEXT,
    compilatore INTEGER,
    compilatoreNominativo TEXT,
    compilatoreFigProf TEXT,
    pressioneMaxOrto REAL,
    pressioneMinOrto REAL,
    pressioneMaxClino REAL,
    pressioneMinClino REAL,
    pressioneMaxNoSpec REAL,
    pressioneMinNoSpec REAL,
    frequenza INTEGER,
    temperatura REAL,
    curvaGli TEXT,
    peso REAL,
    alvo TEXT,
    diuresi TEXT,
    ossigeno TEXT,
    spo2 REAL,
    spo2NoSpec REAL,
    tipoRespirazione TEXT,
    tipoFreqCardiaca TEXT,
    note TEXT,
    sonno TEXT,
    alimentazione TEXT,
    mobilita TEXT,
    dolore TEXT,
    freqRespiratoria INTEGER,
    spo2ot REAL,
    oSpo2ot REAL,
    comportamento TEXT,
    comportamentoAttivita TEXT,
    avpu TEXT,
    altezza REAL,
    malattiaAcuta TEXT,
    notePeso TEXT,
    testDroghe TEXT,
    testDrogheDescr TEXT,
    testAlcool TEXT,
    testGravidanza TEXT,
    bmi REAL,
    inr REAL,
    ciclo TEXT,
    tipoFlusso TEXT,
    ulterioriParametri TEXT,
    punteggioMMSE REAL,
    punteggioCDR REAL,
    vas TEXT,
    vrs TEXT,
    nrs TEXT,
    noppain TEXT,
    noppain55 TEXT,
    painad TEXT,
    visualSkvalMust TEXT,
    mews REAL,
    punteggioMews REAL,
    news REAL,
    punteggioNews REAL,
    parametroATre TEXT,
    listaWarning TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero),
    UNIQUE (idRicovero, data)  -- Prevents duplicate records per patient stay & timestamp
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

    -- Address & Residence (✅ Added `indirizzo` Here)
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

    FOREIGN KEY (codOspite) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
);
""")

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
    idUltimoDett INTEGER,  -- ✅ NEW COLUMN
    idUltimaMedicazioneV1 INTEGER,  -- ✅ NEW COLUMN
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
);
""")

# Create `cirs` table (Indice di Comorbilità CIRS)
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
    FOREIGN KEY (patient_id) REFERENCES patients(idRicovero)
);
""")



# Save and close
conn.commit()
conn.close()

print("✅ Database schema updated with all required fields!")
