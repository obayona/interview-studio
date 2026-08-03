import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft,
  faArrowRight,
  faArrowUp,
  faBars,
  faBolt,
  faBriefcase,
  faCheck,
  faCircleExclamation,
  faCircleInfo,
  faClockRotateLeft,
  faCommentDots,
  faDownload,
  faFileLines,
  faFloppyDisk,
  faGear,
  faHouse,
  faImage,
  faEye,
  faMoon,
  faMicrophone,
  faMicrophoneSlash,
  faPaperPlane,
  faPause,
  faPalette,
  faPhoneSlash,
  faPlus,
  faPlay,
  faRotateRight,
  faSpinner,
  faStop,
  faSun,
  faTrash,
  faUpload,
  faUser,
  faVolumeHigh,
  faVolumeXmark,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';

const icons = {
  arrowLeft: faArrowLeft,
  arrowRight: faArrowRight,
  arrowUp: faArrowUp,
  bars: faBars,
  bolt: faBolt,
  briefcase: faBriefcase,
  check: faCheck,
  error: faCircleExclamation,
  info: faCircleInfo,
  history: faClockRotateLeft,
  interview: faCommentDots,
  download: faDownload,
  view: faEye,
  report: faFileLines,
  save: faFloppyDisk,
  settings: faGear,
  home: faHouse,
  image: faImage,
  moon: faMoon,
  microphone: faMicrophone,
  microphoneOff: faMicrophoneSlash,
  send: faPaperPlane,
  pause: faPause,
  palette: faPalette,
  hangup: faPhoneSlash,
  plus: faPlus,
  play: faPlay,
  resume: faRotateRight,
  spinner: faSpinner,
  stop: faStop,
  sun: faSun,
  trash: faTrash,
  upload: faUpload,
  user: faUser,
  volume: faVolumeHigh,
  volumeOff: faVolumeXmark,
  close: faXmark,
} as const;

export type IconName = keyof typeof icons;

export function Icon({
  name,
  label,
  spin = false,
}: {
  name: IconName;
  label?: string;
  spin?: boolean;
}) {
  return (
    <FontAwesomeIcon
      className="ui-icon"
      icon={icons[name]}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      spin={spin}
    />
  );
}
