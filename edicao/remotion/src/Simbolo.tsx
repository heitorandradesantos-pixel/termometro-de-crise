import { Easing, interpolate, useCurrentFrame } from "remotion";

// O medidor do Termômetro. Com `varrer`, o ponteiro sai da esquerda (frio) e para no lugar dele, como no logo.
export const Simbolo: React.FC<{ tamanho: number; varrer?: boolean; atraso?: number }> = ({
  tamanho,
  varrer = false,
  atraso = 0,
}) => {
  const frame = useCurrentFrame();
  const giro = varrer
    ? interpolate(frame - atraso, [0, 22], [-95, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.34, 1.56, 0.64, 1),
      })
    : 0;
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 200 200">
      <g transform="translate(0,6)">
        <path d="M 38.06 117.3 A 62 62 0 0 1 48.3 85.78" stroke="#3B82C4" strokeWidth={18} fill="none" />
        <path d="M 51.48 81.4 A 62 62 0 0 1 78.29 61.93" stroke="#7CC3E0" strokeWidth={18} fill="none" />
        <path d="M 83.43 60.25 A 62 62 0 0 1 116.57 60.25" stroke="#F2C14E" strokeWidth={18} fill="none" />
        <path d="M 121.71 61.93 A 62 62 0 0 1 148.52 81.4" stroke="#EE8A3C" strokeWidth={18} fill="none" />
        <path d="M 151.7 85.78 A 62 62 0 0 1 161.94 117.3" stroke="#E5554A" strokeWidth={18} fill="none" />
        <line
          x1="100"
          y1="120"
          x2="120.44"
          y2="76.57"
          stroke="#EEF2F5"
          strokeWidth={10}
          strokeLinecap="round"
          transform={`rotate(${giro} 100 120)`}
        />
      </g>
    </svg>
  );
};
