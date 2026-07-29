import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowRight,
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
  faMoon,
  faPalette,
  faSpinner,
  faSun,
  faUser,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';

const icons = {
  arrowRight: faArrowRight,
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
  moon: faMoon,
  palette: faPalette,
  spinner: faSpinner,
  sun: faSun,
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
