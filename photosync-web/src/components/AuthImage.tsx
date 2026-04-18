import { useState, useEffect, useRef } from 'react';
import { api } from '../api/apiClient';

interface AuthImageProps {
  photoId: number;
  thumbnail?: boolean;
  className?: string;
  alt?: string;
}

export default function AuthImage({ photoId, thumbnail = false, className = '', alt = 'Photo' }: AuthImageProps) {
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  
  // 💥 NEW: Track visibility and hold a reference to the DOM element
  const [isVisible, setIsVisible] = useState(false);
  const elementRef = useRef<any>(null);

  // 💥 NEW: The Intersection Observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        // If the element enters the screen (or is within 200px of it)
        if (entries[0].isIntersecting) {
          setIsVisible(true);
          observer.disconnect(); // Stop observing once it triggers to save CPU
        }
      },
      {
        rootMargin: '200px', // Load the image slightly before it scrolls into view
      }
    );

    if (elementRef.current) {
      observer.observe(elementRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, []);

  // Your original fetch logic, now protected by `isVisible`
  useEffect(() => {
    // 💥 STOP HERE if the image hasn't scrolled into view yet!
    if (!isVisible) return;

    let objectUrl: string | null = null;
    let isMounted = true;

    const fetchImage = async () => {
      try {
        const response = await api.get(`/photos/file/${photoId}`, {
          params: { thumbnail },
          responseType: 'blob', 
        });

        if (isMounted) {
          objectUrl = URL.createObjectURL(response.data);
          setImgSrc(objectUrl);
        }
      } catch (err) {
        if (isMounted) setError(true);
        console.error(`Failed to load photo ${photoId}`, err);
      }
    };

    fetchImage();

    return () => {
      isMounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [photoId, thumbnail, isVisible]); // Added isVisible to dependency array

  if (error) {
    return (
      <div ref={elementRef} className={`bg-gray-200 flex items-center justify-center ${className}`}>
        <span className="text-gray-400 text-sm">Unavailable</span>
      </div>
    );
  }

  if (!imgSrc) {
    // 💥 Attach the ref to the placeholder so the observer can watch it
    return <div ref={elementRef} className={`bg-gray-100 animate-pulse ${className}`} />;
  }

  return (
    <img 
      ref={elementRef} 
      src={imgSrc} 
      alt={alt} 
      className={className} 
      loading="lazy" 
    />
  );
}