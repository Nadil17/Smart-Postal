// App.jsx  –  Smart Postal Route Optimizer (Expo Go)
// ─────────────────────────────────────────────────────
// Navigation:  Stack navigator wrapping all screens
// ─────────────────────────────────────────────────────

import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import UploadScreen        from './screens/UploadScreen';
import MailListScreen      from './screens/MailListScreen';
import RoutesScreen        from './screens/RoutesScreen';
import AutoReroutingScreen from './screens/AutoReroutingScreen';
import RelocationScreen    from './screens/RelocationScreen';

const Stack = createStackNavigator();

const HEADER_STYLE = {
  backgroundColor: '#1e40af',
};
const HEADER_TITLE_STYLE = {
  color: '#fff',
  fontWeight: '700',
};

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <NavigationContainer>
          <StatusBar style="light" backgroundColor="#1e40af" />
          <Stack.Navigator
            initialRouteName="Upload"
            screenOptions={{
              headerStyle: HEADER_STYLE,
              headerTintColor: '#fff',
              headerTitleStyle: HEADER_TITLE_STYLE,
              headerBackTitleVisible: false,
            }}
          >
            <Stack.Screen
              name="Upload"
              component={UploadScreen}
              options={{ title: '🗺️ Postal Route Optimizer', headerLeft: () => null }}
            />
            <Stack.Screen
              name="MailList"
              component={MailListScreen}
              options={({ route }) => ({
                title: `📦 Mail List (${route.params?.deliveries?.length || 0} stops)`,
              })}
            />
            <Stack.Screen
              name="Routes"
              component={RoutesScreen}
              options={{ title: '🚀 Optimized Routes' }}
            />
            <Stack.Screen
              name="AutoRerouting"
              component={AutoReroutingScreen}
              options={{ title: '🚨 Auto-Rerouting' }}
            />
            <Stack.Screen
              name="Relocation"
              component={RelocationScreen}
              options={{ title: '📍 Customer Relocation' }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
