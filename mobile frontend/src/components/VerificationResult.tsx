import { CheckCircle, XCircle, Box, Link, Shield, FileCheck } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

interface BlockchainProof {
    recorded: boolean;
    tx_hash: string;
    block_number: number;
    commitment_hash: string;
}

interface VerificationResultProps {
    status: 'success' | 'failed' | 'locker';
    onReset: () => void;
    blockchainProof?: BlockchainProof;
    similarity?: number;
    confidence?: number;
}

const VerificationResult = ({ status, onReset, blockchainProof, similarity, confidence }: VerificationResultProps) => {
    return (
        <div className="flex flex-col items-center justify-center p-6 text-center">
            <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className={clsx(
                    "w-24 h-24 rounded-full flex items-center justify-center mb-4",
                    status === 'success' ? "bg-green-100 text-green-600" :
                        status === 'failed' ? "bg-red-100 text-red-600" :
                            "bg-orange-100 text-orange-600"
                )}
            >
                {status === 'success' && <CheckCircle size={48} />}
                {status === 'failed' && <XCircle size={48} />}
                {status === 'locker' && <Box size={48} />}
            </motion.div>

            <h2 className="text-xl font-bold mb-2">
                {status === 'success' ? "Identity Verified!" :
                    status === 'failed' ? "Verification Failed" :
                        "Redirected to Smart Locker"}
            </h2>

            <p className="text-gray-600 mb-4">
                {status === 'success' ? "The neighbor's face matches the NIC provided. You may hand over the parcel." :
                    status === 'failed' ? "Face does not match the NIC. Please try again or use Smart Locker." :
                        "Due to verification failure, please deposit the parcel at the nearest Smart Locker."}
            </p>

            {/* Verification Metrics */}
            {(similarity !== undefined || confidence !== undefined) && (
                <div className="w-full bg-gray-50 rounded-xl p-3 mb-4">
                    <div className="flex justify-around text-sm">
                        {similarity !== undefined && (
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">{(similarity * 100).toFixed(1)}%</div>
                                <div className="text-gray-500 text-xs">Similarity</div>
                            </div>
                        )}
                        {confidence !== undefined && (
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">{(confidence * 100).toFixed(1)}%</div>
                                <div className="text-gray-500 text-xs">Confidence</div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Blockchain Proof Section */}
            {blockchainProof?.recorded && (
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="w-full bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-4 mb-4 border border-purple-100"
                >
                    <div className="flex items-center justify-center gap-2 mb-3">
                        <Link size={16} className="text-purple-600" />
                        <span className="text-sm font-semibold text-purple-700">Blockchain Verified</span>
                        <Shield size={14} className="text-green-500" />
                    </div>
                    
                    <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
                            <span className="text-gray-500">Block #</span>
                            <span className="font-mono font-semibold text-purple-700">
                                {blockchainProof.block_number}
                            </span>
                        </div>
                        
                        <div className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
                            <span className="text-gray-500">TX Hash</span>
                            <span className="font-mono text-purple-600 truncate max-w-[150px]">
                                {blockchainProof.tx_hash.slice(0, 10)}...{blockchainProof.tx_hash.slice(-6)}
                            </span>
                        </div>
                        
                        <div className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
                            <span className="text-gray-500">Commitment</span>
                            <span className="font-mono text-blue-600 truncate max-w-[150px]">
                                {blockchainProof.commitment_hash}
                            </span>
                        </div>
                    </div>
                    
                    <div className="mt-3 flex items-center justify-center gap-1 text-xs text-gray-500">
                        <FileCheck size={12} />
                        <span>Privacy-preserving proof recorded on-chain</span>
                    </div>
                </motion.div>
            )}

            <div className="flex gap-3 w-full">
                <button
                    onClick={onReset}
                    className="flex-1 py-3 px-4 rounded-xl border border-gray-200 font-medium hover:bg-gray-50"
                >
                    Try Again
                </button>
                {status === 'failed' && (
                    <button
                        className="flex-1 py-3 px-4 rounded-xl bg-orange-600 text-white font-medium hover:bg-orange-700"
                    >
                        Use Locker
                    </button>
                )}
            </div>
        </div>
    );
};

export default VerificationResult;
