import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, ScrollView, SafeAreaView, KeyboardAvoidingView, Platform, Modal, ActivityIndicator } from 'react-native';
import { Mic, Send, Paperclip, CheckCircle2, AlertCircle } from 'lucide-react-native';

const API_BASE_URL = 'http://localhost:8000'; // Make sure backend is running here

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I am your Industrial Knowledge Copilot. You can ask me about maintenance procedures, safety guidelines, or equipment details. How can I help you today?',
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [docModalVisible, setDocModalVisible] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    const userQuery = input.trim();
    const userMsg = { id: Date.now().toString(), role: 'user', content: userQuery };
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery, user_id: 'mobile_user' }),
      });
      
      if (!response.ok) throw new Error('Network response was not ok');
      
      const data = await response.json();
      
      const formatCitations = data.citations ? data.citations.map((c, i) => ({
        id: c.doc_id || `c${i}`,
        title: c.title || c.doc_id || `Document ${i+1}`,
        page: c.page || 1
      })) : [];

      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.answer,
        confidence: data.confidence,
        citations: formatCitations
      }]);
    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: "Sorry, I couldn't connect to the Copilot backend. Ensure the server is running.",
        confidence: 'Low'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const openCitation = (citation) => {
    setSelectedCitation(citation);
    setDocModalVisible(true);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Industrial Copilot</Text>
        <View style={styles.statusBadge}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>Online</Text>
        </View>
      </View>

      <ScrollView style={styles.messageList} contentContainerStyle={{ padding: 16 }}>
        {messages.map((msg) => (
          <View key={msg.id} style={[styles.messageBubble, msg.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
            <Text style={[styles.messageText, msg.role === 'user' ? styles.userText : styles.assistantText]}>
              {msg.content}
            </Text>
            
            {msg.confidence && (
              <View style={styles.metaContainer}>
                <View style={styles.confidenceBadge}>
                  {msg.confidence === 'High' ? <CheckCircle2 size={12} color="#10b981" /> : <AlertCircle size={12} color="#fbbf24" />}
                  <Text style={[styles.confidenceText, { color: msg.confidence === 'High' ? '#10b981' : '#fbbf24' }]}>
                    {msg.confidence} Confidence
                  </Text>
                </View>
                
                {msg.citations && msg.citations.length > 0 && msg.citations.map((c, i) => (
                  <TouchableOpacity key={i} style={styles.citationBadge} onPress={() => openCitation(c)}>
                    <Paperclip size={10} color="#3b82f6" />
                    <Text style={styles.citationText}>[{i + 1}] {c.title}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </View>
        ))}
        {isLoading && (
          <View style={[styles.messageBubble, styles.assistantBubble, { alignSelf: 'flex-start', padding: 10 }]}>
            <ActivityIndicator color="#e2e8f0" size="small" />
          </View>
        )}
      </ScrollView>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.inputContainer}>
        <TouchableOpacity style={styles.iconButton}>
          <Mic size={24} color="#94a3b8" />
        </TouchableOpacity>
        <TextInput
          style={styles.textInput}
          placeholder="Ask a question..."
          placeholderTextColor="#64748b"
          value={input}
          onChangeText={setInput}
          multiline
        />
        <TouchableOpacity style={[styles.iconButton, { backgroundColor: '#3b82f6', borderRadius: 20 }]} onPress={sendMessage} disabled={isLoading}>
          <Send size={18} color="#ffffff" />
        </TouchableOpacity>
      </KeyboardAvoidingView>

      <Modal visible={docModalVisible} animationType="slide" presentationStyle="pageSheet">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{selectedCitation?.title}</Text>
            <TouchableOpacity onPress={() => setDocModalVisible(false)}>
              <Text style={styles.closeButton}>Close</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.pdfViewer}>
            <Text style={{ color: '#64748b' }}>PDF Viewer (Page {selectedCitation?.page})</Text>
            <View style={styles.boundingBoxMock} />
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  header: {
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  headerTitle: {
    color: '#f8fafc',
    fontSize: 18,
    fontWeight: '600',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10b981',
    marginRight: 6,
  },
  statusText: {
    color: '#10b981',
    fontSize: 12,
    fontWeight: '500',
  },
  messageList: {
    flex: 1,
  },
  messageBubble: {
    maxWidth: '85%',
    padding: 14,
    borderRadius: 16,
    marginBottom: 16,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#3b82f6',
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(30, 41, 59, 0.8)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userText: {
    color: '#ffffff',
  },
  assistantText: {
    color: '#e2e8f0',
  },
  metaContainer: {
    marginTop: 12,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  confidenceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.2)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  confidenceText: {
    fontSize: 11,
    fontWeight: '600',
  },
  citationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  citationText: {
    color: '#60a5fa',
    fontSize: 11,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    paddingBottom: Platform.OS === 'ios' ? 24 : 12,
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
    alignItems: 'flex-end',
  },
  iconButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 4,
  },
  textInput: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 20,
    color: '#f8fafc',
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 10,
    minHeight: 40,
    maxHeight: 120,
    marginHorizontal: 8,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  modalTitle: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '600',
  },
  closeButton: {
    color: '#3b82f6',
    fontWeight: '500',
  },
  pdfViewer: {
    flex: 1,
    backgroundColor: '#1e293b',
    justifyContent: 'center',
    alignItems: 'center',
  },
  boundingBoxMock: {
    position: 'absolute',
    top: '30%',
    width: '60%',
    height: 100,
    borderWidth: 2,
    borderColor: 'rgba(251, 191, 36, 0.8)',
    backgroundColor: 'rgba(251, 191, 36, 0.2)',
    borderRadius: 4,
  }
});
