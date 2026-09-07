import React, { useRef, useState } from 'react';
import * as THREE from 'three';
import type { ThreeEvent } from '@react-three/fiber';

interface FielderMarkerProps {
  name: string;
  x: number;
  y: number;
  role: 'wicket_taking' | 'run_saving' | 'core';
  onUpdate: (x: number, y: number) => void;
  showCoverage?: boolean;
}

export const FielderMarker: React.FC<FielderMarkerProps> = ({
  name,
  x,
  y,
  role,
  onUpdate,
  showCoverage = true
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState<boolean>(false);
  const [active, setActive] = useState<boolean>(false);

  const safeName = name || 'Fielder';

  // Map role to color
  const getColor = () => {
    if (safeName === 'Wicketkeeper') return '#d4af37'; // Gold
    if (safeName === 'Bowler') return '#ffffff'; // White
    if (role === 'wicket_taking') return '#ff3b30'; // Red
    return '#007aff'; // Blue
  };

  const getCoverageRadius = () => {
    if (safeName.includes('Slip') || safeName === 'Gully' || safeName === 'Short Leg' || safeName === 'Wicketkeeper') return 4.5;
    if (role === 'wicket_taking') return 8.0;
    if (safeName.startsWith('Deep') || safeName.startsWith('Long') || safeName === 'Third Man' || safeName === 'Fine Leg') return 22.0;
    return 12.5;
  };

  const color = getColor();
  const coverageRadius = getCoverageRadius();

  // Drag handler using R3F pointer events
  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setActive(true);
  };

  const handlePointerMove = (e: ThreeEvent<PointerEvent>) => {
    if (!active) return;
    e.stopPropagation();
    
    const newX = e.unprojectedPoint.x;
    const newY = e.unprojectedPoint.z;

    const dist = Math.sqrt(newX * newX + newY * newY);
    if (dist <= 65) {
      onUpdate(newX, newY);
    } else {
      const angle = Math.atan2(newY, newX);
      onUpdate(Math.cos(angle) * 65, Math.sin(angle) * 65);
    }
  };

  const handlePointerUp = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    setActive(false);
  };

  return (
    <group>
      {/* Draggable sphere */}
      <mesh
        ref={meshRef}
        position={[x, 0.5, y]} // Height is 0.5 so it sits on the ground
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[1.2, 16, 16]} />
        <meshStandardMaterial
          color={hovered || active ? '#58a6ff' : color}
          roughness={0.4}
          metalness={0.1}
          emissive={active ? '#58a6ff' : '#000000'}
          emissiveIntensity={0.2}
        />
      </mesh>

      {/* Shadow element on the ground */}
      <mesh position={[x, 0.01, y]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0, 1.4]} />
        <meshBasicMaterial color="#000000" opacity={0.3} transparent />
      </mesh>

      {/* Fielder Intercept Coverage Radius Ring */}
      {showCoverage && (
        <mesh position={[x, 0.02, y]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[coverageRadius - 0.25, coverageRadius, 32]} />
          <meshBasicMaterial color={color} opacity={0.35} transparent side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
};
