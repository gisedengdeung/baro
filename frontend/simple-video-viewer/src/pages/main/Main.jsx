import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../../assets/style.css';

function Main() {
  const [showIntro, setShowIntro] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowIntro(false);
      navigate('/intro');
    }, 2500);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <>
      {showIntro && (
        <div className="intro">
          <h1 className="intro-title">Conveyor Guard</h1>
          <div className="line"></div>
          <p className="intro-subtitle">Welcome to Conveyor Guard</p>
        </div>
      )}
    </>
  );
}

export default Main;
