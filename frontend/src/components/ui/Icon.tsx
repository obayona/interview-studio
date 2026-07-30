import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
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
  faFileLines,
  faGear,
  faHouse,
  faImage,
  faMoon,
  faPalette,
  faPlus,
  faSpinner,
  faSun,
  faTrash,
  faUpload,
  faUser,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';

const icons = {
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
  report: faFileLines,
  settings: faGear,
  home: faHouse,
  image: faImage,
  moon: faMoon,
  palette: faPalette,
  plus: faPlus,
  spinner: faSpinner,
  sun: faSun,
  trash: faTrash,
  upload: faUpload,
  user: faUser,
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
