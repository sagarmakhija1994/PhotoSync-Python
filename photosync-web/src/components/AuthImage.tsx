import { useState, useEffect } from 'react';
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

  useEffect(() => {
    let objectUrl: string | null = null;
    let isMounted = true;

    const fetchImage = async () => {
      try {
        // Fetch the image as a Blob, letting the apiClient attach the JWT
        const response = await api.get(`/photos/file/${photoId}`, {
          params: { thumbnail },
          responseType: 'blob', // Crucial: tell Axios we expect a binary file
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

    // Cleanup the Blob URL when the component unmounts to prevent memory leaks
    return () => {
      isMounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [photoId, thumbnail]);

  if (error) {
    return (
      <div className={`bg-gray-200 flex items-center justify-center ${className}`}>
        <span className="text-gray-400 text-sm">Unavailable</span>
      </div>
    );
  }

  if (!imgSrc) {
    return <div className={`bg-gray-100 animate-pulse ${className}`} />;
  }

  return <img src={imgSrc} alt={alt} className={className} loading="lazy" />;
}