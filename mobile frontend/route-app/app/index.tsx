import { Text, View, StyleSheet, Animated, Dimensions } from "react-native";
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useRef } from "react";
import { BlurView } from 'expo-blur';

const { width, height } = Dimensions.get('window');

export default function Index() {
  const floatAnim1 = useRef(new Animated.Value(0)).current;
  const floatAnim2 = useRef(new Animated.Value(0)).current;
  const floatAnim3 = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    // Entrance animation
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1200,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous floating animations for background orbs
    const createFloatingAnimation = (animValue: Animated.Value, duration: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.timing(animValue, {
            toValue: 1,
            duration: duration,
            useNativeDriver: true,
          }),
          Animated.timing(animValue, {
            toValue: 0,
            duration: duration,
            useNativeDriver: true,
          }),
        ])
      );
    };

    createFloatingAnimation(floatAnim1, 4000).start();
    createFloatingAnimation(floatAnim2, 5000).start();
    createFloatingAnimation(floatAnim3, 6000).start();
  }, []);

  const orb1TranslateY = floatAnim1.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 30],
  });

  const orb2TranslateY = floatAnim2.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -40],
  });

  const orb3TranslateY = floatAnim3.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 25],
  });

  return (
    <View style={styles.container}>
      {/* Animated gradient background */}
      <LinearGradient
        colors={['#0f0c29', '#302b63', '#24243e']}
        style={StyleSheet.absoluteFillObject}
      />

      {/* Floating orbs */}
      <Animated.View
        style={[
          styles.orb,
          styles.orb1,
          { transform: [{ translateY: orb1TranslateY }] },
        ]}
      >
        <LinearGradient
          colors={['#ff6b9d', '#c06c84']}
          style={styles.orbGradient}
        />
      </Animated.View>

      <Animated.View
        style={[
          styles.orb,
          styles.orb2,
          { transform: [{ translateY: orb2TranslateY }] },
        ]}
      >
        <LinearGradient
          colors={['#4facfe', '#00f2fe']}
          style={styles.orbGradient}
        />
      </Animated.View>

      <Animated.View
        style={[
          styles.orb,
          styles.orb3,
          { transform: [{ translateY: orb3TranslateY }] },
        ]}
      >
        <LinearGradient
          colors={['#43e97b', '#38f9d7']}
          style={styles.orbGradient}
        />
      </Animated.View>

      {/* Main content with glassmorphism */}
      <Animated.View
        style={[
          styles.glassCard,
          {
            opacity: fadeAnim,
            transform: [{ scale: scaleAnim }],
          },
        ]}
      >
        <BlurView intensity={20} tint="dark" style={styles.blurContainer}>
          <View style={styles.cardContent}>
            {/* Decorative corner accent */}
            <View style={styles.cornerAccent} />
            
            <Text style={styles.emoji}>✨</Text>
            
            <Text style={styles.title}>Welcome</Text>
            
            <Text style={styles.subtitle}>
              Your canvas awaits
            </Text>
            
            <View style={styles.divider} />
            
            <Text style={styles.bodyText}>
              Edit app/index.tsx to bring your vision to life
            </Text>
            
            {/* Animated pulse indicator */}
            <View style={styles.pulseContainer}>
              <View style={styles.pulseRing} />
              <View style={styles.pulseDot} />
            </View>
          </View>
        </BlurView>
      </Animated.View>

      {/* Ambient glow effects */}
      <View style={[styles.ambientGlow, styles.glowTop]} />
      <View style={[styles.ambientGlow, styles.glowBottom]} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  orb: {
    position: 'absolute',
    borderRadius: 200,
    opacity: 0.3,
  },
  orb1: {
    width: 280,
    height: 280,
    top: '10%',
    left: -100,
  },
  orb2: {
    width: 200,
    height: 200,
    top: '60%',
    right: -50,
  },
  orb3: {
    width: 240,
    height: 240,
    bottom: '15%',
    left: '50%',
  },
  orbGradient: {
    flex: 1,
    borderRadius: 200,
  },
  glassCard: {
    width: width * 0.85,
    borderRadius: 32,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.5,
    shadowRadius: 40,
    elevation: 20,
  },
  blurContainer: {
    padding: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  cardContent: {
    alignItems: 'center',
  },
  cornerAccent: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 60,
    height: 60,
    borderTopRightRadius: 32,
    borderBottomLeftRadius: 60,
    backgroundColor: 'rgba(67, 233, 123, 0.2)',
  },
  emoji: {
    fontSize: 56,
    marginBottom: 20,
  },
  title: {
    fontSize: 48,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -1,
    marginBottom: 8,
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  subtitle: {
    fontSize: 18,
    color: 'rgba(255, 255, 255, 0.7)',
    fontWeight: '500',
    letterSpacing: 2,
    textTransform: 'uppercase',
    marginBottom: 24,
  },
  divider: {
    width: 60,
    height: 3,
    backgroundColor: 'rgba(67, 233, 123, 0.6)',
    borderRadius: 2,
    marginBottom: 24,
  },
  bodyText: {
    fontSize: 15,
    color: 'rgba(255, 255, 255, 0.6)',
    textAlign: 'center',
    lineHeight: 22,
    maxWidth: 280,
    marginBottom: 32,
  },
  pulseContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 50,
    height: 50,
  },
  pulseRing: {
    position: 'absolute',
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2,
    borderColor: 'rgba(67, 233, 123, 0.4)',
  },
  pulseDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#43e97b',
  },
  ambientGlow: {
    position: 'absolute',
    width: width,
    height: 200,
    opacity: 0.1,
  },
  glowTop: {
    top: 0,
    backgroundColor: '#4facfe',
  },
  glowBottom: {
    bottom: 0,
    backgroundColor: '#ff6b9d',
  },
});