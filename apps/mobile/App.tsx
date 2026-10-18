import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable,
  SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { api, ChatHistory, clearSession, Conversation, getSession, Intro, Me, Person, saveSession } from './src/api';
import { colors } from './src/theme';

type AuthResult = { access_token: string };
type Screen = 'home' | 'profile' | 'chat';
type ReportReason = 'harassment' | 'spam' | 'impersonation' | 'safety' | 'other';

function Action({ title, onPress, warning = false, disabled = false }: {
  title: string;
  onPress: () => void;
  warning?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress}
      style={[styles.button, warning && styles.warningButton, disabled && { opacity: 0.5 }]}>
      <Text style={[styles.buttonText, warning && { color: colors.text }]}>{title}</Text>
    </Pressable>
  );
}

function Field({ label, value, onChangeText, secureTextEntry = false, keyboardType = 'default',
  multiline = false }: {
    label: string;
    value: string;
    onChangeText: (s: string) => void;
    secureTextEntry?: boolean;
    keyboardType?: 'default' | 'email-address' | 'number-pad';
    multiline?: boolean;
  }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && { minHeight: 86 }]}
        value={value} onChangeText={onChangeText}
        secureTextEntry={secureTextEntry} keyboardType={keyboardType}
        multiline={multiline} autoCapitalize={keyboardType === 'email-address' ? 'none' : 'sentences'}
        placeholderTextColor={colors.muted}
        accessibilityLabel={label}
      />
    </View>
  );
}

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [age, setAge] = useState('25');
  const [me, setMe] = useState<Me | null>(null);
  const [screen, setScreen] = useState<Screen>('home');
  const [bio, setBio] = useState('');
  const [values, setValues] = useState('życzliwość, uczciwość');
  const [minAge, setMinAge] = useState('18');
  const [maxAge, setMaxAge] = useState('60');
  const [today, setToday] = useState<Intro | null>(null);
  const [inbox, setInbox] = useState<Intro[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [history, setHistory] = useState<ChatHistory | null>(null);
  const [message, setMessage] = useState('');
  const [reportFor, setReportFor] = useState<Person | null>(null);
  const [reportReason, setReportReason] = useState<ReportReason>('safety');
  const [reportDetails, setReportDetails] = useState('');

  const load = async (key: string) => {
    const profile = await api<Me>('/api/v1/me', 'GET', undefined, key);
    setMe(profile);
    setName(profile.display_name);
    setBio(profile.bio);
    setValues(profile.values.join(', '));
    setMinAge(String(profile.min_age));
    setMaxAge(String(profile.max_age));
    const [newInbox, newConversations, newToday] = await Promise.all([
      api<Intro[]>('/api/v1/introductions/inbox', 'GET', undefined, key),
      api<Conversation[]>('/api/v1/conversations', 'GET', undefined, key),
      profile.ready
        ? api<Intro>('/api/v1/introductions/today', 'GET', undefined, key)
        : Promise.resolve(null),
    ]);
    setInbox(newInbox);
    setConversations(newConversations);
    setToday(newToday);
  };

  useEffect(() => {
    let alive = true;
    (async () => {
      const stored = await getSession();
      if (stored) {
        try {
          await load(stored);
          if (alive) setToken(stored);
        } catch {
          await clearSession();
        }
      }
      if (alive) setBooting(false);
    })().catch(() => { if (alive) setBooting(false); });
    return () => { alive = false; };
  }, []);

  const execute = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try { await fn(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Nieznany błąd'); }
    finally { setBusy(false); }
  };

  const authenticate = () => execute(async () => {
    const body = isRegister
      ? { email, password, display_name: name, age: Number(age) }
      : { email, password };
    const response = await api<AuthResult>(
      isRegister ? '/api/v1/auth/register' : '/api/v1/auth/token',
      'POST', body,
    );
    await saveSession(response.access_token);
    setToken(response.access_token);
    setPassword('');
    await load(response.access_token);
    setScreen(isRegister ? 'profile' : 'home');
  });

  const refresh = () => execute(async () => {
    if (token) await load(token);
  });

  const saveProfile = () => execute(async () => {
    if (!token) return;
    const selectedValues = values.split(',').map(v => v.trim()).filter(Boolean);
    await api('/api/v1/me', 'PUT', {
      display_name: name, bio, values: selectedValues,
      min_age: Number(minAge), max_age: Number(maxAge), ready: true,
    }, token);
    await load(token);
    setScreen('home');
  });

  const decide = (introId: string, decision: 'accept' | 'decline') =>
    execute(async () => {
      if (!token) return;
      await api(`/api/v1/introductions/${introId}/${decision}`, 'POST', {}, token);
      await load(token);
    });

  const openChat = (conv: Conversation) => execute(async () => {
    if (!token) return;
    setHistory(await api<ChatHistory>(
      `/api/v1/conversations/${conv.id}/messages`, 'GET', undefined, token));
    setSelected(conv);
    setScreen('chat');
  });

  const sendMessage = () => execute(async () => {
    if (!token || !selected || !message.trim()) return;
    await api(`/api/v1/conversations/${selected.id}/messages`, 'POST',
      { content: message.trim() }, token);
    setMessage('');
    setHistory(await api<ChatHistory>(
      `/api/v1/conversations/${selected.id}/messages`, 'GET', undefined, token));
  });

  const closeConversation = () => {
    if (!token || !selected) return;
    Alert.alert('Zakończyć rozmowę?', 'Nie będzie możliwe wysyłanie nowych wiadomości.', [
      { text: 'Anuluj', style: 'cancel' },
      { text: 'Zakończ', style: 'destructive', onPress: () => execute(async () => {
        await api(`/api/v1/conversations/${selected.id}/close`, 'POST', {}, token);
        setSelected(null);
        setScreen('home');
        await load(token);
      }) },
    ]);
  };

  const block = (person: Person) => {
    if (!token) return;
    Alert.alert('Zablokować osobę?', 'Zostaną zamknięte wszystkie wasze rozmowy.', [
      { text: 'Anuluj', style: 'cancel' },
      { text: 'Blokuj', style: 'destructive', onPress: () => execute(async () => {
        await api(`/api/v1/safety/blocks/${person.id}`, 'POST', {}, token);
        setSelected(null);
        setScreen('home');
        await load(token);
      }) },
    ]);
  };

  const submitReport = () => execute(async () => {
    if (!token || !reportFor) return;
    await api('/api/v1/safety/reports', 'POST', {
      subject_id: reportFor.id, reason: reportReason, details: reportDetails,
    }, token);
    setReportFor(null);
    setReportDetails('');
    Alert.alert('Zgłoszenie zapisane', 'Dziękujemy za zgłoszenie. Obsługa spraw zgłoszonych wymaga uruchomienia zespołu moderacji.');
  });

  const logout = () => execute(async () => {
    await clearSession();
    setToken(null);
    setMe(null);
    setScreen('home');
    setSelected(null);
    setHistory(null);
  });

  const deleteAccount = () => {
    if (!token) return;
    Alert.alert('Usunąć konto i wiadomości?', 'Operacja jest nieodwracalna.', [
      { text: 'Anuluj', style: 'cancel' },
      { text: 'Usuń konto', style: 'destructive', onPress: () => execute(async () => {
        await api('/api/v1/me', 'DELETE', undefined, token);
        await clearSession();
        setToken(null);
        setMe(null);
        setScreen('home');
      }) },
    ]);
  };

  const renderPerson = (person: Person) => (
    <View style={styles.person}>
      <Text style={styles.personTitle}>{person.display_name}, {person.age}</Text>
      <Text style={styles.body}>{person.bio || 'Bez opisu'}</Text>
      <Text style={styles.muted}>{person.values.join(' · ')}</Text>
      <View style={styles.actions}>
        <Action title="Zgłoś" onPress={() => setReportFor(person)} />
        <Action title="Blokuj" warning onPress={() => block(person)} />
      </View>
    </View>
  );

  const renderIntro = (intro: Intro, title: string) => {
    if (!intro.person || !intro.id || intro.declined) return null;
    const accepted = me?.id === intro.person.id ? intro.candidate_accepted : intro.owner_accepted;
    return (
      <View key={intro.id} style={styles.panel}>
        <Text style={styles.heading}>{title}</Text>
        {renderPerson(intro.person)}
        <Text style={styles.muted}>{accepted ? 'Twoja zgoda została zapisana.' : 'Rozmowa wymaga zgody obu osób.'}</Text>
        <View style={styles.actions}>
          <Action title="Chcę poznać" disabled={busy || Boolean(accepted)}
            onPress={() => decide(intro.id!, 'accept')} />
          <Action title="Pomiń" warning disabled={busy}
            onPress={() => decide(intro.id!, 'decline')} />
        </View>
      </View>
    );
  };

  if (booting) {
    return <SafeAreaView style={styles.page}><ActivityIndicator color={colors.cyan} size="large" /></SafeAreaView>;
  }
  return (
    <SafeAreaView style={styles.page}>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          <Text style={styles.logo}>AURA<Text style={{ color: colors.cyan }}>.</Text></Text>
          <Text style={styles.tagline}>Mniej profili. Więcej prawdziwej rozmowy.</Text>
          {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
          {busy && <ActivityIndicator style={{ marginVertical: 8 }} color={colors.cyan} />}

          {!token ? (
            <View style={styles.panel}>
              <Text style={styles.heading}>{isRegister ? 'Utwórz konto' : 'Zaloguj się'}</Text>
              <Field label="Adres e-mail" value={email} onChangeText={setEmail} keyboardType="email-address" />
              <Field label="Hasło (minimum 12 znaków)" value={password} onChangeText={setPassword} secureTextEntry />
              {isRegister && <>
                <Field label="Jak mamy Cię nazywać?" value={name} onChangeText={setName} />
                <Field label="Wiek — tylko osoby 18+" value={age} onChangeText={setAge} keyboardType="number-pad" />
              </>}
              <Action title={isRegister ? 'Zarejestruj' : 'Zaloguj'} disabled={busy} onPress={authenticate} />
              <Action title={isRegister ? 'Mam już konto' : 'Nie mam konta'} disabled={busy}
                onPress={() => { setIsRegister(!isRegister); setError(null); }} />
              <Text style={styles.muted}>Wersja techniczna. Nie przeznaczona do publicznego rejestrowania użytkowników.</Text>
            </View>
          ) : <>
            <View style={styles.actions}>
              <Action title="Dzisiaj" onPress={() => setScreen('home')} />
              <Action title="Mój profil" onPress={() => setScreen('profile')} />
              <Action title="Wyloguj" onPress={logout} />
            </View>

            {screen === 'profile' && (
              <View style={styles.panel}>
                <Text style={styles.heading}>Twój profil</Text>
                <Field label="Imię lub pseudonim" value={name} onChangeText={setName} />
                <Field label="Kilka słów o sobie" value={bio} onChangeText={setBio} multiline />
                <Field label="Wartości — oddziel przecinkami" value={values} onChangeText={setValues} />
                <Field label="Minimalny wiek drugiej osoby" value={minAge} onChangeText={setMinAge} keyboardType="number-pad" />
                <Field label="Maksymalny wiek drugiej osoby" value={maxAge} onChangeText={setMaxAge} keyboardType="number-pad" />
                <Action title="Zapisz i aktywuj profil" disabled={busy} onPress={saveProfile} />
                <Action title="Usuń moje konto" warning onPress={deleteAccount} />
              </View>
            )}

            {screen === 'home' && <>
              <View style={styles.panel}>
                <Text style={styles.heading}>Witaj, {me?.display_name}</Text>
                {!me?.ready
                  ? <Action title="Dokończ profil" onPress={() => setScreen('profile')} />
                  : <>
                    <Text style={styles.muted}>Jedno nowe wprowadzenie na dobę (UTC), bez przesuwania profili.</Text>
                    <Action title="Odśwież" disabled={busy} onPress={refresh} />
                  </>}
              </View>
              {me?.ready && <>
                {today?.person ? renderIntro(today, 'Dzisiejszy rezonans')
                  : <View style={styles.panel}><Text style={styles.body}>Dzisiaj nie ma nowej propozycji.</Text></View>}
                {inbox.map(item => renderIntro(item, 'Ktoś chce Cię poznać'))}
                <View style={styles.panel}>
                  <Text style={styles.heading}>Rozmowy ({conversations.length}/3)</Text>
                  {conversations.length === 0 && <Text style={styles.muted}>Rozmowa rozpoczyna się po wzajemnej zgodzie.</Text>}
                  {conversations.map(c => <View key={c.id} style={styles.space}>
                    <Action title={`Otwórz: ${c.person.display_name}`} onPress={() => openChat(c)} />
                  </View>)}
                </View>
              </>}
            </>}

            {screen === 'chat' && selected && (
              <View style={styles.panel}>
                <Text style={styles.heading}>Rozmowa: {selected.person.display_name}</Text>
                <Text style={styles.muted}>
                  Etap odsłaniania: {history?.reveal_stage === 'unlocked' ? 'odblokowany' : 'ukryty'}
                  {' · '}{history?.meaningful_messages ?? 0}/20 wiadomości
                </Text>
                {history?.items.map(m => (
                  <View style={styles.chatRow} key={m.id}>
                    <Text style={styles.muted}>{m.author_id === me?.id ? 'Ty' : selected.person.display_name}</Text>
                    <Text style={styles.body}>{m.content}</Text>
                  </View>
                ))}
                <Field label="Twoja wiadomość" value={message} onChangeText={setMessage} multiline />
                <Action title="Wyślij wiadomość" disabled={busy || !message.trim()} onPress={sendMessage} />
                <Action title="Odśwież rozmowę" onPress={() => openChat(selected)} />
                {renderPerson(selected.person)}
                <Action title="Zakończ rozmowę" warning onPress={closeConversation} />
                <Action title="Wróć" onPress={() => setScreen('home')} />
              </View>
            )}
          </>}

          {token && reportFor && (
            <View style={styles.panel}>
              <Text style={styles.heading}>Zgłoś: {reportFor.display_name}</Text>
              <View style={styles.actions}>
                {(['harassment', 'spam', 'impersonation', 'safety', 'other'] as ReportReason[]).map(reason =>
                  <Action key={reason} title={reason === reportReason ? `✓ ${reason}` : reason}
                    onPress={() => setReportReason(reason)} />
                )}
              </View>
              <Field label="Szczegóły (opcjonalnie)" value={reportDetails} onChangeText={setReportDetails} multiline />
              <Action title="Wyślij zgłoszenie" disabled={busy} onPress={submitReport} />
              <Action title="Anuluj" onPress={() => setReportFor(null)} />
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  content: { paddingHorizontal: 18, paddingTop: 28, paddingBottom: 70, gap: 18 },
  logo: { fontWeight: '900', fontSize: 44, color: colors.text, letterSpacing: 3 },
  tagline: { color: colors.muted, fontSize: 14, marginTop: -12 },
  panel: { padding: 18, gap: 12, borderWidth: 1, borderColor: colors.border,
    backgroundColor: colors.panel, borderRadius: 8 },
  heading: { color: colors.text, fontWeight: '800', fontSize: 20 },
  person: { paddingVertical: 10, gap: 8 },
  personTitle: { color: colors.cyan, fontWeight: '800', fontSize: 20 },
  body: { color: colors.text, fontSize: 16, lineHeight: 24 },
  muted: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  field: { gap: 6 },
  label: { color: colors.text, fontWeight: '700', fontSize: 14 },
  input: { backgroundColor: colors.bg, borderColor: colors.border, borderWidth: 1,
    paddingHorizontal: 12, paddingVertical: 12, color: colors.text, borderRadius: 6, fontSize: 16 },
  button: { backgroundColor: colors.cyan, paddingHorizontal: 12, paddingVertical: 12,
    borderRadius: 6, alignItems: 'center', marginVertical: 2, minHeight: 44, justifyContent: 'center' },
  buttonText: { color: colors.bg, fontWeight: '800', fontSize: 14 },
  warningButton: { backgroundColor: colors.danger },
  actions: { gap: 7, flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center' },
  space: { paddingVertical: 6 },
  chatRow: { paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border, gap: 4 },
  error: { backgroundColor: '#531A2A', color: '#FFFFFF', padding: 12, borderRadius: 6 },
});
